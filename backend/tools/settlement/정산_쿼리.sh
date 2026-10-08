#!/usr/bin/env bash
# 월 정산 데이터 추출 (studio 컨테이너가 도는 서버에서 실행)
# 사용: ./정산_쿼리.sh 2026-09 > 정산_202609.tsv
# 기준: 교정(WF_STS_HRV_350) '최초 완료'가 해당 월인 회차 → 그 회차의 싱크(WF_STS_SYN_202)는 완료일 무관 포함
set -euo pipefail
YM="${1:?YYYY-MM}"
sudo docker exec -i -e YM="$YM" viewlingo-studio-backend python - <<'EOF'
import math, os
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.database import engine
from app.routers.settings import genre_label

KST = timezone(timedelta(hours=9))
y, m = map(int, os.environ["YM"].split("-"))
START = datetime(y, m, 1, tzinfo=KST)
END = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=KST)

SQL = r"""
WITH done AS (
  SELECT l.prj_id, l.sts_cd, l.reg_dt, l.req_id,
    row_number() OVER (PARTITION BY l.prj_id, l.sts_cd
                       ORDER BY l.reg_dt) AS rn
  FROM t_cap_job_log l
  WHERE l.sts_cd IN ('WF_STS_SYN_202', 'WF_STS_HRV_350')
    AND l.del_yn = 'N'
)
SELECT p.id AS prj_id, p.del_yn AS prj_del, b.brd_nm, g.gnr_cd,
  COALESCE(g.prg_nm, p.program_name) AS prg_nm,
  p.season, p.episode, p.name AS prj_nm,
  (SELECT max(bs.brd_dt) FROM t_biz_item bi
     JOIN t_biz_sup bs ON bs.biz_item_id = bi.biz_item_id
    WHERE bi.prj_id = p.id AND bi.del_yn = 'N'
      AND bs.del_yn = 'N') AS brd_dt,
  CASE WHEN d.sts_cd = 'WF_STS_SYN_202' THEN 'SYNC' ELSE 'EDIT' END AS wk,
  ua.display_name AS asg_nm, uc.display_name AS done_by,
  d.reg_dt AS done_at,
  (SELECT max(v.dur_ms) FROM t_vdo v
    WHERE v.prj_id = p.id AND v.del_yn = 'N') AS dur_ms,
  (SELECT sum(w.elapsed_seconds) FROM project_work_time w
    WHERE w.project_id = p.id AND w.phase IN
      (CASE WHEN d.sts_cd = 'WF_STS_SYN_202' THEN 'sync' ELSE 'edit' END,
       CASE WHEN d.sts_cd = 'WF_STS_SYN_202' THEN 'resync' ELSE 'reedit' END)
  ) AS work_sec
FROM done d
JOIN projects p ON p.id = d.prj_id
LEFT JOIN t_brd b ON b.brd_id = p.brd_id
LEFT JOIN t_prg g ON g.prg_id = p.prg_id
LEFT JOIN t_prj_asg a ON a.prj_id = p.id AND a.del_yn = 'N'
  AND a.role_cd = CASE WHEN d.sts_cd = 'WF_STS_SYN_202'
                       THEN 'sync' ELSE 'edit' END
LEFT JOIN users ua ON ua.id = a.usr_id
LEFT JOIN users uc ON uc.id = CASE
  WHEN split_part(d.req_id, ':', 2) = 'user'
   AND split_part(d.req_id, ':', 3) ~ '^[0-9]+$'
  THEN split_part(d.req_id, ':', 3)::bigint END
WHERE d.rn = 1
  AND d.prj_id IN (
    SELECT e.prj_id FROM done e
     WHERE e.sts_cd = 'WF_STS_HRV_350' AND e.rn = 1
       AND e.reg_dt >= :start AND e.reg_dt < :end)
ORDER BY b.brd_nm, prg_nm, p.episode, wk
"""

HDR = ["prj_id", "deleted", "brd", "genre", "program", "season",
       "episode", "prj_name", "air_date", "work", "assignee",
       "done_by", "first_done_kst", "dur_ms", "dur_min_ceil",
       "work_min"]

def clean(v):
    return "" if v is None else str(v).replace("\t", " ").replace("\n", " ")

with engine.connect() as c:
    rows = c.execute(text(SQL), {"start": START, "end": END}).mappings().all()

print("\t".join(HDR))
for r in rows:
    dur = r["dur_ms"]
    ws = r["work_sec"]
    out = [
        r["prj_id"], "Y" if r["prj_del"] in ("Y", True) else "N", r["brd_nm"],
        genre_label(r["gnr_cd"]), r["prg_nm"], r["season"],
        r["episode"], r["prj_nm"], r["brd_dt"], r["wk"],
        r["asg_nm"], r["done_by"],
        r["done_at"].astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        dur, math.ceil(dur / 60000) if dur else "",
        round(ws / 60, 1) if ws else "",
    ]
    print("\t".join(clean(v) for v in out))
print("# rows=%d" % len(rows))
EOF
