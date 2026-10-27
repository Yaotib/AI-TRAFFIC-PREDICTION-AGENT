
import { TopBar } from "../components/TopBar";
import { LocationPanel } from "../components/LocationPanel";
import { SidebarFooter } from "../components/SidebarFooter";
import { LiveStatusBar } from "../components/LiveStatusBar";
import { JourneyPlanner } from "../components/JourneyPlanner";
import { MapPanel } from "./MapPanel";

export default function App() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50 font-sans">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        <aside
          id="route-sidebar"
          className="flex w-[360px] shrink-0 flex-col overflow-y-auto border-r border-gray-100 bg-white shadow-sm"
        >
          <LocationPanel />

          <div className="mx-4 h-px bg-gray-100" />

          <div className="flex-1 pt-3">
            <JourneyPlanner />
          </div>

          <SidebarFooter />
        </aside>

        <main
          id="map-container"
          className="relative flex-1 overflow-hidden"
        >
          <MapPanel />
          <LiveStatusBar />
        </main>
      </div>
    </div>
  );
}
