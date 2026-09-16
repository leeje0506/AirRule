import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

export default function AppLayout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" style={{ fontFamily: "'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif" }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          {/* h-full 을 넘겨줘야 테스트·검증처럼 화면을 꽉 채우는 페이지가
              뷰포트 안에서 자기 영역만 스크롤할 수 있다. 내용이 더 긴 일반
              페이지는 이 컨테이너가 그대로 스크롤한다. */}
          <div className="h-full overflow-y-auto">
            <div className="max-w-screen-xl mx-auto w-full h-full">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}