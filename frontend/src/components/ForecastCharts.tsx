import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

export type PredictionPoint = {
  time: string;
  ra: number;
  dec: number;
  distanceFromSunAU?: number;
  distanceFromEarthAU?: number;
};

type ForecastChartsProps = {
  predictions: PredictionPoint[];
  selectedIndex: number;
};

function ForecastCharts({ predictions, selectedIndex }: ForecastChartsProps) {
  const raDecSvgRef = useRef<SVGSVGElement | null>(null);
  const sunDistanceSvgRef = useRef<SVGSVGElement | null>(null);
  const earthDistanceSvgRef = useRef<SVGSVGElement | null>(null);

  const parsedData = useMemo(() => {
    return predictions.map((point, index) => ({
      ...point,
      index,
      date: new Date(point.time),
      distanceFromSunAU:
        typeof point.distanceFromSunAU === "number" ? point.distanceFromSunAU : null,
      distanceFromEarthAU:
        typeof point.distanceFromEarthAU === "number" ? point.distanceFromEarthAU : null,
    }));
  }, [predictions]);

  useEffect(() => {
    if (!raDecSvgRef.current || parsedData.length === 0) return;

    const svg = d3.select(raDecSvgRef.current);
    svg.selectAll("*").remove();

    const width = 720;
    const height = 260;
    const margin = { top: 24, right: 28, bottom: 42, left: 54 };

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const x = d3
      .scaleLinear()
      .domain(d3.extent(parsedData, (d) => d.index) as [number, number])
      .range([margin.left, width - margin.right]);

    const allValues = parsedData.flatMap((d) => [d.ra, d.dec]);
    const y = d3
      .scaleLinear()
      .domain(d3.extent(allValues) as [number, number])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const xAxis = d3.axisBottom(x).ticks(6).tickFormat((d) => `Day ${Number(d) + 1}`);
    const yAxis = d3.axisLeft(y).ticks(5);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(xAxis);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(${margin.left},0)`)
      .call(yAxis);

    const grid = d3.axisLeft(y).ticks(5).tickSize(-(width - margin.left - margin.right)).tickFormat(() => "");
    svg.append("g")
      .attr("class", "d3-grid")
      .attr("transform", `translate(${margin.left},0)`)
      .call(grid);

    const raLine = d3.line<(typeof parsedData)[number]>()
      .x((d) => x(d.index))
      .y((d) => y(d.ra))
      .curve(d3.curveMonotoneX);

    const decLine = d3.line<(typeof parsedData)[number]>()
      .x((d) => x(d.index))
      .y((d) => y(d.dec))
      .curve(d3.curveMonotoneX);

    svg.append("path").datum(parsedData).attr("class", "d3-line d3-line-ra").attr("d", raLine);
    svg.append("path").datum(parsedData).attr("class", "d3-line d3-line-dec").attr("d", decLine);

    const safeIndex = Math.min(selectedIndex, parsedData.length - 1);
    const selected = parsedData[safeIndex];

    if (selected) {
      svg.append("line")
        .attr("class", "d3-selected-line")
        .attr("x1", x(selected.index))
        .attr("x2", x(selected.index))
        .attr("y1", margin.top)
        .attr("y2", height - margin.bottom);

      svg.append("circle")
        .attr("class", "d3-selected-point d3-selected-ra")
        .attr("cx", x(selected.index))
        .attr("cy", y(selected.ra))
        .attr("r", 6);

      svg.append("circle")
        .attr("class", "d3-selected-point d3-selected-dec")
        .attr("cx", x(selected.index))
        .attr("cy", y(selected.dec))
        .attr("r", 6);

      svg.append("text")
        .attr("class", "d3-selected-label")
        .attr("x", x(selected.index) + 8)
        .attr("y", margin.top + 12)
        .text(`Day ${safeIndex + 1}`);
    }
  }, [parsedData, selectedIndex]);

  useEffect(() => {
    if (!sunDistanceSvgRef.current || parsedData.length === 0) return;

    const distanceData = parsedData.filter((d) => d.distanceFromSunAU !== null);
    const svg = d3.select(sunDistanceSvgRef.current);
    svg.selectAll("*").remove();

    const width = 720;
    const height = 220;
    const margin = { top: 24, right: 28, bottom: 42, left: 54 };

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    if (distanceData.length === 0) {
      svg.append("text")
        .attr("class", "d3-empty-text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .text("Distance from Sun data is not available yet.");
      return;
    }

    const x = d3.scaleLinear()
      .domain(d3.extent(distanceData, (d) => d.index) as [number, number])
      .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
      .domain(d3.extent(distanceData, (d) => d.distanceFromSunAU as number) as [number, number])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const xAxis = d3.axisBottom(x).ticks(6).tickFormat((d) => `Day ${Number(d) + 1}`);
    const yAxis = d3.axisLeft(y).ticks(5);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(xAxis);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(${margin.left},0)`)
      .call(yAxis);

    const grid = d3.axisLeft(y).ticks(5).tickSize(-(width - margin.left - margin.right)).tickFormat(() => "");
    svg.append("g")
      .attr("class", "d3-grid")
      .attr("transform", `translate(${margin.left},0)`)
      .call(grid);

    const distanceLine = d3.line<(typeof distanceData)[number]>()
      .x((d) => x(d.index))
      .y((d) => y(d.distanceFromSunAU as number))
      .curve(d3.curveMonotoneX);

    svg.append("path")
      .datum(distanceData)
      .attr("class", "d3-line d3-line-distance")
      .attr("d", distanceLine);

    const safeIndex = Math.min(selectedIndex, distanceData.length - 1);
    const selected = distanceData[safeIndex];

    if (selected) {
      svg.append("line")
        .attr("class", "d3-selected-line")
        .attr("x1", x(selected.index))
        .attr("x2", x(selected.index))
        .attr("y1", margin.top)
        .attr("y2", height - margin.bottom);

      svg.append("circle")
        .attr("class", "d3-selected-point d3-selected-distance")
        .attr("cx", x(selected.index))
        .attr("cy", y(selected.distanceFromSunAU as number))
        .attr("r", 6);
    }
  }, [parsedData, selectedIndex]);

  useEffect(() => {
    if (!earthDistanceSvgRef.current || parsedData.length === 0) return;

    const distanceData = parsedData.filter((d) => d.distanceFromEarthAU !== null);
    const svg = d3.select(earthDistanceSvgRef.current);
    svg.selectAll("*").remove();

    const width = 720;
    const height = 220;
    const margin = { top: 24, right: 28, bottom: 42, left: 54 };

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    if (distanceData.length === 0) {
      svg.append("text")
        .attr("class", "d3-empty-text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .text("Distance from Earth data is not available yet.");
      return;
    }

    const x = d3.scaleLinear()
      .domain(d3.extent(distanceData, (d) => d.index) as [number, number])
      .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
      .domain(d3.extent(distanceData, (d) => d.distanceFromEarthAU as number) as [number, number])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const xAxis = d3.axisBottom(x).ticks(6).tickFormat((d) => `Day ${Number(d) + 1}`);
    const yAxis = d3.axisLeft(y).ticks(5);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(xAxis);

    svg.append("g")
      .attr("class", "d3-axis")
      .attr("transform", `translate(${margin.left},0)`)
      .call(yAxis);

    const grid = d3.axisLeft(y).ticks(5).tickSize(-(width - margin.left - margin.right)).tickFormat(() => "");
    svg.append("g")
      .attr("class", "d3-grid")
      .attr("transform", `translate(${margin.left},0)`)
      .call(grid);

    const distanceLine = d3.line<(typeof distanceData)[number]>()
      .x((d) => x(d.index))
      .y((d) => y(d.distanceFromEarthAU as number))
      .curve(d3.curveMonotoneX);

    svg.append("path")
      .datum(distanceData)
      .attr("class", "d3-line d3-line-earth-distance")
      .attr("d", distanceLine);

    const safeIndex = Math.min(selectedIndex, distanceData.length - 1);
    const selected = distanceData[safeIndex];

    if (selected) {
      svg.append("line")
        .attr("class", "d3-selected-line")
        .attr("x1", x(selected.index))
        .attr("x2", x(selected.index))
        .attr("y1", margin.top)
        .attr("y2", height - margin.bottom);

      svg.append("circle")
        .attr("class", "d3-selected-point d3-selected-earth-distance")
        .attr("cx", x(selected.index))
        .attr("cy", y(selected.distanceFromEarthAU as number))
        .attr("r", 6);
    }
  }, [parsedData, selectedIndex]);

  return (
    <div className="forecast-charts">
      <div className="forecast-chart-card">
        <div className="forecast-chart-header">
          <h4>RA / DEC Forecast Over Time</h4>
          <p>Predicted celestial position of the asteroid across the selected time range.</p>
        </div>
        <svg ref={raDecSvgRef} className="d3-chart"></svg>
        <div className="chart-legend">
          <span><i className="legend-ra"></i>RA</span>
          <span><i className="legend-dec"></i>DEC</span>
        </div>
      </div>

      <div className="forecast-chart-card">
        <div className="forecast-chart-header">
          <h4>Distance from Sun Over Time</h4>
          <p>Estimated heliocentric distance of the asteroid in AU.</p>
        </div>
        <svg ref={sunDistanceSvgRef} className="d3-chart distance-chart"></svg>
        <div className="chart-legend">
          <span><i className="legend-distance"></i>Distance from Sun AU</span>
        </div>
      </div>

      <div className="forecast-chart-card">
        <div className="forecast-chart-header">
          <h4>Distance from Earth Over Time</h4>
          <p>Estimated geocentric distance of the asteroid in AU.</p>
        </div>
        <svg ref={earthDistanceSvgRef} className="d3-chart distance-chart"></svg>
        <div className="chart-legend">
          <span><i className="legend-earth-distance"></i>Distance from Earth AU</span>
        </div>
      </div>
    </div>
  );
}

export default ForecastCharts;