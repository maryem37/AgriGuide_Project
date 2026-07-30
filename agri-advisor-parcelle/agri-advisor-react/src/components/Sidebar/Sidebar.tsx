import type { SelectionStatus } from "../../hooks/useParcelSelection";
import type { NeighborCropContext, ParcelResolution } from "../../types/api";
import { Header } from "../Header";
import { ActionButtons } from "./ActionButtons";
import { NeighborCard } from "./NeighborCard";
import { StatusCard } from "./StatusCard";
import "./Sidebar.css";

interface SidebarProps {
  status: SelectionStatus;
  message: string;
  parcel: ParcelResolution | null;
  neighbors: NeighborCropContext | null;
  ndviAvailable: boolean;
  ndviActive: boolean;
  ndviLoading: boolean;
  adviseLoading: boolean;
  onToggleNdvi: () => void;
  onAdvise: () => void;
}

export function Sidebar({
  status,
  message,
  parcel,
  neighbors,
  ndviAvailable,
  ndviActive,
  ndviLoading,
  adviseLoading,
  onToggleNdvi,
  onAdvise,
}: SidebarProps) {
  return (
    <div className="sidebar">
      <Header />
      <StatusCard status={status} message={message} parcel={parcel} />
      <NeighborCard neighbors={neighbors} />
      <ActionButtons
        parcelSelected={parcel !== null}
        ndviAvailable={ndviAvailable}
        ndviActive={ndviActive}
        ndviLoading={ndviLoading}
        adviseLoading={adviseLoading}
        onToggleNdvi={onToggleNdvi}
        onAdvise={onAdvise}
      />
    </div>
  );
}
