import AdminSummaryDetailPage from "./SummaryDetailPage";

// 静的出力（output: "export"）では動的ルートの全パスを事前に列挙する必要がある。
// 詳細はクライアント側で useParams から取得して API を呼ぶため、ここでは仮の 1 件だけを出力する。
export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "0" }];
}

export default function Page() {
  return <AdminSummaryDetailPage />;
}
