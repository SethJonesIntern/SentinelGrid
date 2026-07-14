export default function MapPage() {
  return (
    <div
      style={{
        width: "100%",
        height: "calc(100vh - 100px)",
        minHeight: 700,
        borderRadius: 14,
        overflow: "hidden",
        background: "#05070c",
      }}
    >
      <iframe
        title="SentinelGrid Map"
        src="/live-threat-map.html"
        style={{ width: "100%", height: "100%", border: 0 }}
      />
    </div>
  );
}
