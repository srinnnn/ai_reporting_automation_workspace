import { Outlet } from "react-router-dom";
import { PlatformShell, PlatformSidebar, PlatformTopbar } from "../components/platform";

export function AppLayout() {
  return (
    <PlatformShell sidebar={<PlatformSidebar />} topbar={<PlatformTopbar />}>
      <Outlet />
    </PlatformShell>
  );
}
