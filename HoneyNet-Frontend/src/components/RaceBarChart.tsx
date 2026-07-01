import { useEffect, useRef } from "react";
import * as echarts from "echarts";

export interface RaceBarDatum {
  label: string;
  value: number;
  fill: string;
}

export default function RaceBarChart({ data, height = 260 }: { data: RaceBarDatum[]; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current);
    chartRef.current = chart;

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Categories stay in a fixed order — `realtimeSort` figures out the
    // ranked visual position itself and animates bars sliding into place
    // whenever the underlying values change (e.g. after a redistribute).
    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(4,8,20,0.97)",
        borderColor: "rgba(59,130,246,0.3)",
        borderWidth: 1,
        textStyle: { color: "#e2e8f4", fontFamily: "'Space Mono', monospace", fontSize: 12 },
        formatter: (p) => {
          const item = Array.isArray(p) ? p[0] : p;
          return `<b>${item.name}</b>: ${item.value}`;
        }
      },
      grid: { left: 90, right: 46, top: 10, bottom: 10, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: "#4b5f7c", fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } }
      },
      yAxis: {
        type: "category",
        data: data.map((d) => d.label),
        inverse: true,
        axisLabel: { color: "#8896b0", fontSize: 11, fontFamily: "'Space Mono', monospace" },
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.15)" } },
        axisTick: { show: false },
        animationDuration: 700,
        animationDurationUpdate: 700
      },
      series: [{
        type: "bar",
        realtimeSort: true,
        data: data.map((d) => ({ value: d.value, itemStyle: { color: d.fill } })),
        barMaxWidth: 26,
        label: {
          show: true,
          position: "right",
          color: "#e2e8f4",
          fontWeight: 700,
          fontFamily: "'Space Mono', monospace"
        }
      }],
      animationDuration: 700,
      animationDurationUpdate: 700,
      animationEasing: "cubicOut",
      animationEasingUpdate: "cubicOut"
    };

    chart.setOption(option);
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
