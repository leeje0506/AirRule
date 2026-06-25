"""
TechItem 시드 데이터 — config yaml 기반 함수 단위 매핑
"""
from app.models import TechItem


def get_tech_items():
    items = []

    def _add(id, tp, name, fn, ft, stage, desc="", params=None, scope="common", tag="applied"):
        items.append(TechItem(
            id=id, type=tp, name=name, function_name=fn,
            func_type=ft, stage=stage, desc=desc,
            params=params or {}, scope=scope, tag=tag, source_code="",
        ))

    # ── Stage 1 Common 후처리 ──
    _add("s1_pp_strip", "processing", "문장 앞뒤 공백 제거", "postprocess_strip_whitespace", "content_only", "stage1")
    _add("s1_pp_trim", "processing", "괄호 안쪽 공백 제거", "postprocess_trim_speaker_spaces", "content_only", "stage1")
    _add("s1_pp_spk", "processing", "화자 뒤 공백 추가", "postprocess_add_speaker_space", "content_only", "stage1")
    _add("s1_pp_nsp", "processing", "연속 공백 정규화", "postprocess_normalize_spaces", "content_only", "stage1")
    _add("s1_pp_asp", "processing", "특수기호 뒤 공백 추가", "postprocess_add_space_after_special_punctuation", "content_only", "stage1")
    _add("s1_pp_wrp", "processing", "잘못된 기호 제거", "postprocess_remove_wrong_punctuation", "content_only", "stage1")
    _add("s1_pp_ell", "processing", "말줄임표 정규화", "postprocess_normalize_ellipsis", "content_only", "stage1")
    _add("s1_pp_rep", "processing", "반복 특수기호 정규화", "postprocess_normalize_repeats", "content_only", "stage1")
    _add("s1_pp_wmx", "processing", "잘못된 특수문자 정규화", "postprocess_normalize_wrong_mixed_punctuations", "content_only", "stage1")
    _add("s1_pp_mix", "processing", "혼합 특수기호 정규화", "postprocess_normalize_mix_characters", "content_only", "stage1")
    _add("s1_pp_syn", "processing", "싱크 맞닿음 조정", "postprocess_sync_overlap", "timing", "stage1")
    _add("s1_pp_rst", "processing", "인덱스 재부여+정렬", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage1")

    # ── Stage 1 Common 검증 ──
    _add("s1_vl_pair", "validation", "괄호/따옴표 짝 검증", "validate_pair_characters", "content_only", "stage1")
    _add("s1_vl_spec", "validation", "특수문자 검증(♫허용)", "validate_special_characters_allow_music_note", "content_only", "stage1")
    _add("s1_vl_elip", "validation", "말줄임표 개수 검증", "validate_ellipsis_count", "content_with_params", "stage1", params={"criterion": 2})
    _add("s1_vl_sync", "validation", "싱크 마이너스/0 검증", "validate_sync_negative_or_zero", "timing", "stage1")

    # ── Stage 2 Common 후처리 ──
    _add("s2c_pp_asp", "processing", "[공통] 특수기호 뒤 공백", "postprocess_add_space_after_special_punctuation", "content_only", "stage2")

    # ── Stage 2 Common 검증 ──
    _add("s2c_vl_len", "validation", "[공통] 줄별 길이 검증", "validate_length_lines", "content_with_validation_params", "stage2", params={"valid_type": "length"})
    _add("s2c_vl_lnc", "validation", "[공통] 줄 수 검증", "validate_line_count", "content_with_validation_params", "stage2")
    _add("s2c_vl_par", "validation", "[공통] 괄호 짝 검증", "validate_pair_characters", "content_only", "stage2")
    _add("s2c_vl_syn", "validation", "[공통] 싱크 검증", "validate_sync_negative_or_zero", "timing", "stage2")
    _add("s2c_vl_elp", "validation", "[공통] 말줄임표 검증", "validate_ellipsis_count", "content_with_params", "stage2", params={"criterion": 2})

    # ── Stage 2 JTBC ──
    _add("s2_jtbc_vsp", "validation", "[JTBC] 특수문자 검증", "validate_special_characters_allow_music_note", "content_only", "stage2", scope="specific")
    _add("s2_jtbc_vov", "validation", "[JTBC] 오버랩 줄수 검증", "validate_overlapped_over_lines", "pair_validation", "stage2", scope="specific")
    _add("s2_jtbc_pol", "processing", "[JTBC] 18자 줄바꿈", "postprocess_over_length_lines", "content_with_params", "stage2", params={"max_length": 18}, scope="specific")
    _add("s2_jtbc_prm", "processing", "[JTBC] 통합 기호 제거", "postprocess_remove_other_characters", "content_only", "stage2", scope="specific")
    _add("s2_jtbc_pnp", "processing", "[JTBC] 짝 안맞는 문자 제거", "postprocess_remove_not_pair_characters", "content_only", "stage2", scope="specific")
    _add("s2_jtbc_pms", "processing", "[JTBC] 오버랩 다화자 처리", "postprocess_mark_overlapped_multi_speaker", "multi_subtitle", "stage2", params={"reassign_index": True}, scope="specific")
    _add("s2_jtbc_pps", "processing", "[JTBC] 자막간 마침표 삽입", "postprocess_add_period_between_subs", "multi_subtitle", "stage2", scope="specific")
    _add("s2_jtbc_ppl", "processing", "[JTBC] 줄간 마침표 삽입", "postprocess_add_period_between_lines", "content_only", "stage2", scope="specific")
    _add("s2_jtbc_prs", "processing", "[JTBC] 인덱스 재부여", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage2", scope="specific")

    # ── Stage 2 LGHV ──
    _add("s2_lghv_vsp", "validation", "[LGHV] 특수문자 검증", "validate_special_characters_allow_music_note", "content_only", "stage2", scope="specific")
    _add("s2_lghv_vov", "validation", "[LGHV] 오버랩 줄수 검증", "validate_overlapped_over_lines", "pair_validation", "stage2", scope="specific")
    _add("s2_lghv_vot", "validation", "[LGHV] 오버랩 대사만 검증", "validate_overlapped_only_text_for_lghv", "pair_validation", "stage2", scope="specific")
    _add("s2_lghv_pol", "processing", "[LGHV] 18자 줄바꿈", "postprocess_over_length_lines", "content_with_params", "stage2", params={"max_length": 18}, scope="specific")
    _add("s2_lghv_psa", "processing", "[LGHV] 별표/꺾쇠 제거", "postprocess_remove_star_and_angle_for_lghv", "content_only", "stage2", scope="specific")
    _add("s2_lghv_pnp", "processing", "[LGHV] 짝 안맞는 문자 제거", "postprocess_remove_not_pair_paren_quotes_for_lghv", "content_only", "stage2", scope="specific")
    _add("s2_lghv_pmn", "processing", "[LGHV] 음표 ♫ 통일", "postprocess_normalize_music_to_double_note_for_lghv", "content_only", "stage2", scope="specific")
    _add("s2_lghv_pkb", "processing", "[LGHV] [♫ ...]만 보존", "postprocess_keep_bracket_music_note_and_remove_others_for_lghv", "content_only", "stage2", scope="specific")
    _add("s2_lghv_pms", "processing", "[LGHV] 오버랩 다화자 처리", "postprocess_mark_overlapped_multi_speaker", "multi_subtitle", "stage2", params={"reassign_index": True}, scope="specific")
    _add("s2_lghv_pps", "processing", "[LGHV] 자막간 마침표 삽입", "postprocess_add_period_between_subs", "multi_subtitle", "stage2", scope="specific")
    _add("s2_lghv_ppl", "processing", "[LGHV] 줄간 마침표 삽입", "postprocess_add_period_between_lines", "content_only", "stage2", scope="specific")
    _add("s2_lghv_prs", "processing", "[LGHV] 인덱스 재부여", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage2", scope="specific")

    # ── Stage 2 SKBB ──
    _add("s2_skbb_vsc", "validation", "[SKBB] 특수문자 검증", "validate_special_characters", "content_only", "stage2", scope="specific")
    _add("s2_skbb_vhy", "validation", "[SKBB] 하이픈 공백 검증", "validate_hyphen_no_space_after_for_skbb", "content_only", "stage2", scope="specific")
    _add("s2_skbb_vmo", "validation", "[SKBB] 모자이크 개수 검증", "validate_mosaic_count_for_skbb", "content_with_params", "stage2", params={"criterion": 2}, scope="specific")
    _add("s2_skbb_vov", "validation", "[SKBB] 오버랩 줄수 검증", "validate_overlapped_over_lines", "pair_validation", "stage2", scope="specific")
    _add("s2_skbb_vso", "validation", "[SKBB] 오버랩 존재 검증", "validate_sync_overlapped", "pair_validation", "stage2", scope="specific")
    _add("s2_skbb_pfh", "processing", "[SKBB] 첫 하이픈 제거", "postprocess_remove_first_hypn", "content_with_params", "stage2", params={"punctuation": "-"}, scope="specific")
    _add("s2_skbb_psh", "processing", "[SKBB] 하이픈 뒤 공백 제거", "postprocess_remove_space_after_hypn", "content_only", "stage2", scope="specific")
    _add("s2_skbb_psa", "processing", "[SKBB] 미허용 기호 제거", "postprocess_remove_star_and_angle_for_skbb", "content_only", "stage2", scope="specific")
    _add("s2_skbb_pnp", "processing", "[SKBB] 짝 안맞는 문자 제거", "postprocess_remove_not_pair_paren_quotes_for_skbb", "content_only", "stage2", scope="specific")
    _add("s2_skbb_pas", "processing", "[SKBB] 별표 정규화", "postprocess_normalize_asterisk_for_skbb", "content_only", "stage2", scope="specific")
    _add("s2_skbb_pps", "processing", "[SKBB] 자막간 마침표 삽입", "postprocess_add_period_between_subs", "multi_subtitle", "stage2", scope="specific")
    _add("s2_skbb_ppl", "processing", "[SKBB] 줄간 마침표 삽입", "postprocess_add_period_between_lines", "content_only", "stage2", scope="specific")
    _add("s2_skbb_prs", "processing", "[SKBB] 인덱스 재부여", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage2", scope="specific")

    # ── Stage 2 TVNG (TVING) ──
    _add("s2_tvng_pmn", "processing", "[TVING] 음표 ♪ 통일", "postprocess_normalize_music_to_single_note_for_tvng", "content_only", "stage2", scope="specific")
    _add("s2_tvng_pps", "processing", "[TVING] 자막간 마침표 삽입", "postprocess_add_period_between_subs", "multi_subtitle", "stage2", scope="specific")
    _add("s2_tvng_ppl", "processing", "[TVING] 줄간 마침표 삽입", "postprocess_add_period_between_lines", "content_only", "stage2", scope="specific")
    _add("s2_tvng_prs", "processing", "[TVING] 인덱스 재부여", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage2", scope="specific")

    # ── Stage 2 DLIV ──
    _add("s2_dliv_vhy", "validation", "[DLIV] 하이픈 공백 검증", "validate_hyphen_no_space_after_for_skbb", "content_only", "stage2", scope="specific")
    _add("s2_dliv_vsd", "validation", "[DLIV] 1초 미만 싱크 검증", "validate_sync_short_duration", "timing", "stage2", params={"min_duration_sec": 1.0}, scope="specific")
    _add("s2_dliv_val", "validation", "[DLIV] 연속 오버랩 줄수 검증", "validate_overlapped_accumulated_lines", "multi_validation", "stage2", params={"max_lines": 3}, scope="specific")
    _add("s2_dliv_psh", "processing", "[DLIV] 하이픈 뒤 공백 제거", "postprocess_remove_space_after_hypn", "content_only", "stage2", scope="specific")
    _add("s2_dliv_pms", "processing", "[DLIV] 오버랩 다화자 처리", "postprocess_mark_overlapped_multi_speaker", "multi_subtitle", "stage2",
         params={"reassign_index": True, "multi_speaker_prefix": "", "max_lines_per_sub": 3, "multi_overlap_strategy": "merge_all", "max_merged_lines": 3}, scope="specific")
    _add("s2_dliv_pag", "processing", "[DLIV] 자막 간격 조정", "postprocess_adjust_subtitle_gaps", "multi_subtitle", "stage2", params={"gap_sec": 0.083}, scope="specific")
    _add("s2_dliv_pam", "processing", "[DLIV] 1초 미만 자막 처리", "postprocess_adjust_or_merge_short_sync", "multi_subtitle", "stage2",
         params={"min_duration_sec": 1.0, "max_lines_after_merge": 3, "gap_sec": 0.083}, scope="specific")
    _add("s2_dliv_pps", "processing", "[DLIV] 자막간 마침표 삽입", "postprocess_add_period_between_subs", "multi_subtitle", "stage2", scope="specific")
    _add("s2_dliv_ppl", "processing", "[DLIV] 줄간 마침표 삽입", "postprocess_add_period_between_lines", "content_only", "stage2", scope="specific")
    _add("s2_dliv_prs", "processing", "[DLIV] 인덱스 재부여", "postprocess_reset_subtitles_from_list", "multi_subtitle", "stage2", scope="specific")

    # TVCS: 현재 extend 비어있음 (공통만 적용)

    # ── Stage 3 최종 납품 (final_postprocess) ──
    # 마침표 삭제 — config remove_punctuation=true 인 방송사 (LGHV / JTBC / TVING)
    _add("s3_lghv_prp", "processing", "[LGHV] 마침표 삭제(납품)", "postprocess_remove_last_punctuation", "content_with_params", "final", params={"punctuation": ["."]}, scope="specific", desc="최종 납품 시 단일 마침표 제거 (말줄임표·소수·영문약어 보존)")
    _add("s3_jtbc_prp", "processing", "[JTBC] 마침표 삭제(납품)", "postprocess_remove_last_punctuation", "content_with_params", "final", params={"punctuation": ["."]}, scope="specific", desc="최종 납품 시 단일 마침표 제거 (말줄임표·소수·영문약어 보존)")
    _add("s3_tvng_prp", "processing", "[TVING] 마침표 삭제(납품)", "postprocess_remove_last_punctuation", "content_with_params", "final", params={"punctuation": ["."]}, scope="specific", desc="최종 납품 시 단일 마침표 제거 (말줄임표·소수·영문약어 보존)")

    # 배너 삽입 — config banner=true 인 방송사 (JTBC / TVCS)
    _add("s3_jtbc_pbn", "processing", "[JTBC] 배너 싱크 삽입(납품)", "postprocess_add_banner_subtitle", "multi_subtitle", "final",
         params={"banner_sentence": "장애인방송 VOD 제작지원 : 방송미디어통신위원회‧시청자미디어재단", "banner_start": "00:00:00", "banner_end": "00:05:00"},
         scope="specific", desc="장애인방송 제작지원 배너 자막을 맨 앞에 삽입 (00:00~05:00)")
    _add("s3_tvcs_pbn", "processing", "[TVCS] 배너 싱크 삽입(납품)", "postprocess_add_banner_subtitle", "multi_subtitle", "final",
         params={"banner_sentence": "장애인방송 VOD 제작지원 : 방송미디어통신위원회‧시청자미디어재단", "banner_start": "00:00:00", "banner_end": "00:00:07"},
         scope="specific", desc="장애인방송 제작지원 배너 자막을 맨 앞에 삽입 (00:00~00:07)")

    return items