import { Dashboard } from "./Dashboard";
import type { DashboardData } from "./types";
import data from "../public/data/dashboard.json";

export default function Page() {
  return <Dashboard data={data as DashboardData} />;
}
