import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import "../App.css";
import ForecastCharts from "../components/ForecastCharts";

type ObservationItem = {
  id?: string;
  fileName: string;
  uploadedBy: string;
  uploadedAt: string;
  count: number;
  status: string;
  invalidReason?: string;
  visibility: "private" | "public";
  orbitalElementId?: string;
};

type OrbitalElementResult = {
  id: string;
  observationSetId: string;
  uploadedBy: string;
  fileName: string;
  calculatedAt: string;
  algorithm: string;
  rmsDeg: number;
  observationsCount: number;
  status: string;
  orbitalElements: {
    a: number;
    e: number;
    Omega: number;
    inc: number;
    omega: number;
    M0: number;
    t0_jd: number;
  };
};

type PredictionPoint = {
  time: string;
  ra: number;
  dec: number;
  distanceFromSunAU?: number;
  distanceFromEarthAU?: number;
};

type PredictionResult = {
  orbitalElementId: string;
  createdAt: string;
  count: number;
  data: PredictionPoint[];
};

type SelectedResult = {
  orbital: OrbitalElementResult;
  predictions: PredictionResult;
};

function Dashboard() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [myObservationHistory, setMyObservationHistory] = useState<ObservationItem[]>([]);
  const [publicObservationHistory, setPublicObservationHistory] = useState<ObservationItem[]>([]);
  const [activeArchive, setActiveArchive] = useState<"my" | "public">("my");
  const [selectedResult, setSelectedResult] = useState<SelectedResult | null>(null);
  const [resultMessage, setResultMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [predictionIndex, setPredictionIndex] = useState(0);

  const loggedInUser = useMemo(() => {
    const storedUser = localStorage.getItem("asteroidtrack_user");

    if (!storedUser) return "Unknown";

    try {
      const parsedUser = JSON.parse(storedUser);
      return parsedUser.username || "Unknown";
    } catch {
      return "Unknown";
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("asteroidtrack_user");
    navigate("/");
  };

  const fetchMyObservations = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/observations/my/${loggedInUser}`);
      const data = await response.json();

      if (response.ok) {
        setMyObservationHistory(data);
      }
    } catch (error) {
      console.error("Failed to fetch my observations:", error);
    }
  };

  const fetchPublicObservations = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/observations/public");
      const data = await response.json();

      if (response.ok) {
        setPublicObservationHistory(data);
      }
    } catch (error) {
      console.error("Failed to fetch public observations:", error);
    }
  };

  const refreshArchives = async () => {
    await Promise.all([fetchMyObservations(), fetchPublicObservations()]);
  };

  useEffect(() => {
    refreshArchives();
  }, [loggedInUser]);

  useEffect(() => {
    setPredictionIndex(0);
  }, [selectedResult]);

  useEffect(() => {
    if (!selectedResult || selectedResult.predictions.data.length === 0) {
      return;
    }

    const timer = window.setInterval(() => {
      setPredictionIndex((currentIndex) => {
        const total = selectedResult.predictions.data.length;
        return (currentIndex + 1) % total;
      });
    }, 1400);

    return () => window.clearInterval(timer);
  }, [selectedResult]);

  const openResultsByOrbitalElementId = async (orbitalElementId: string) => {
    setResultMessage("");

    try {
      const orbitalResponse = await fetch(
        `http://127.0.0.1:8000/orbital-elements/${orbitalElementId}`
      );

      const orbitalData = await orbitalResponse.json();

      if (!orbitalResponse.ok || orbitalData.message) {
        setResultMessage(orbitalData.message || "Failed to load orbital elements");
        return;
      }

      const predictionsResponse = await fetch(
        `http://127.0.0.1:8000/predictions/by-orbital-element/${orbitalElementId}`
      );

      const predictionsData = await predictionsResponse.json();

      setSelectedResult({
        orbital: orbitalData,
        predictions: predictionsData,
      });
    } catch (error) {
      console.error(error);
      setResultMessage("Failed to load orbit results");
    }
  };

  const handleViewResults = async (item: ObservationItem) => {
    if (!item.orbitalElementId) {
      setResultMessage("No orbital result was found for this observation file.");
      return;
    }

    await openResultsByOrbitalElementId(item.orbitalElementId);
  };
  const handleDeleteObservation = async (item: ObservationItem) => {
    if (!item.id) {
      setResultMessage("Observation id is missing.");
      return;
    }
  
    const confirmed = window.confirm(
      "Are you sure you want to delete this observation? Related orbit results and predictions will also be deleted."
    );
  
    if (!confirmed) return;
  
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/observations/${item.id}`,
        { method: "DELETE" }
      );
  
      const data = await response.json();
  
      if (!response.ok || data.message?.includes("not found")) {
        setResultMessage(data.message || "Delete failed");
        return;
      }
  
      setMyObservationHistory((prev) =>
        prev.filter((obs) => obs.id !== item.id)
      );
  
      setPublicObservationHistory((prev) =>
        prev.filter((obs) => obs.id !== item.id)
      );
  
      if (selectedResult?.orbital.observationSetId === item.id) {
        setSelectedResult(null);
      }
  
      setResultMessage("");
    } catch (error) {
      console.error(error);
      setResultMessage("Server error while deleting observation");
    }
  };

  const handleAnalyze = async (item: ObservationItem) => {
    if (!item.id) {
      setResultMessage("Observation id is missing.");
      return;
    }

    setIsAnalyzing(true);
    setResultMessage("");
    setUploadMessage("Running analysis...");

    try {
      const analyzeResponse = await fetch(
        `http://127.0.0.1:8000/observations/${item.id}/analyze`,
        { method: "POST" }
      );

      const analyzeData = await analyzeResponse.json();

      if (!analyzeResponse.ok || analyzeData.error) {
        setResultMessage(analyzeData.message || analyzeData.error || "Analysis failed");
        setUploadMessage("Analysis failed");
        await refreshArchives();
        return;
      }

      if (analyzeData.orbitalElementId) {
        setUploadMessage("Analysis completed successfully");
        await refreshArchives();
        await openResultsByOrbitalElementId(analyzeData.orbitalElementId);
      } else {
        setUploadMessage(analyzeData.message || "Analysis did not return orbital result");
        await refreshArchives();
      }
    } catch (error) {
      console.error(error);
      setResultMessage("Server error during analysis");
      setUploadMessage("Server error during analysis");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadMessage("");
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setUploadMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("uploadedBy", loggedInUser);
    formData.append("visibility", visibility);

    setIsAnalyzing(true);
    setUploadMessage("Uploading file...");

    try {
      const response = await fetch("http://127.0.0.1:8000/observations/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        if (data.status === "Validated") {
          setUploadMessage("Uploaded successfully. Running analysis...");

          const analyzeResponse = await fetch(
            `http://127.0.0.1:8000/observations/${data.id}/analyze`,
            { method: "POST" }
          );

          const analyzeData = await analyzeResponse.json();

          if (analyzeData.orbitalElementId) {
            setUploadMessage("Analysis completed successfully");
            await refreshArchives();
            await openResultsByOrbitalElementId(analyzeData.orbitalElementId);
          } else {
            setUploadMessage(analyzeData.message || "Analysis failed");
            await refreshArchives();
          }
        } else {
          setUploadMessage(data.invalidReason || "File uploaded but failed validation");
          await refreshArchives();
        }
      } else {
        setUploadMessage(data.message || "Upload failed");
      }
    } catch {
      setUploadMessage("Server connection error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const formatNumber = (value: number, digits = 5) => {
    if (typeof value !== "number") return value;
    return value.toFixed(digits);
  };

  const renderStatusClass = (status: string) => {
    if (status === "Validated") return "status-validated";
    if (status === "Invalid") return "status-invalid";
    if (status === "ReadyForOrbitCalculation") return "status-ready";
    if (status === "ProcessingFailed") return "status-processing-failed";
    if (status === "OrbitCalculated") return "status-ready";
    return "status-ready";
  };

  const renderArchiveList = (items: ObservationItem[], emptyTitle: string, emptyText: string) => {
    if (items.length === 0) {
      return (
        <div className="history-list">
          <div className="history-item">
            <div className="history-left">
              <div>
                <div className="history-file">{emptyTitle}</div>
                <div className="history-meta">{emptyText}</div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="history-list">
        {items.map((item, index) => (
          <div className="history-item" key={`${item.fileName}-${item.uploadedAt}-${index}`}>
            <div className="history-left">
              <div className="history-icon">◎</div>
              <div>
                <div className="history-file">{item.fileName}</div>
                <div className="history-meta">
                  {formatDate(item.uploadedAt)} • {item.count} observations • by {item.uploadedBy} • {item.visibility}
                </div>
                {item.status === "Invalid" && item.invalidReason && (
                  <div className="history-error-text">{item.invalidReason}</div>
                )}
              </div>
            </div>

            <div className="history-actions">
              {(item.status === "Validated" ||
                item.status === "ReadyForOrbitCalculation" ||
                item.status === "ProcessingFailed") && (
                <button
                  className="ghost-btn"
                  onClick={() => handleAnalyze(item)}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? "Analyzing..." : "Analyze"}
                </button>
              )}

              {item.status === "OrbitCalculated" && (
                <button className="ghost-btn" onClick={() => handleViewResults(item)}>
                  View Results
                </button>
              )}
              <button
              className="ghost-btn delete-observation-btn"
              onClick={() => handleDeleteObservation(item)}
            >
              Delete
            </button>
              
              <span className={`status-badge ${renderStatusClass(item.status)}`}>
                {item.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-dashboard-page">
      <div className="space-background-glow glow-one"></div>
      <div className="space-background-glow glow-two"></div>

      <header className="mission-topbar">
        <div className="brand-block">
          <div>
            <h1 className="dashboard-brand-title">AsteroidTrack</h1>
            <p className="dashboard-brand-subtitle">
              NEAR-EARTH OBJECT MONITORING SYSTEM
            </p>
          </div>
        </div>

        <div className="topbar-right">
          <div className="system-pill">
            <span className="live-dot"></span>
            SYSTEM ONLINE
          </div>

          <div className="user-chip">
            <span className="user-label">Operator</span>
            <span className="user-name">{loggedInUser}</span>
          </div>

          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-grid">
        <section className="orbit-panel glass-card">
          <div className="section-header">
            <span className="section-tag">Live Visualization</span>
            <h2>Orbital Monitoring Console</h2>
            <p>
              Current visual view of the solar system environment and tracked
              observation zone.
            </p>
          </div>

          <div className="solar-visual">
            <div className="space-stars-layer">
              <span className="space-star star-a"></span>
              <span className="space-star star-b"></span>
              <span className="space-star star-c"></span>
              <span className="space-star star-d"></span>
              <span className="space-star star-e"></span>
              <span className="space-star star-f"></span>
              <span className="space-star star-g"></span>
              <span className="space-star star-h"></span>
              <span className="space-star star-i"></span>
              <span className="space-star star-j"></span>
              <span className="space-star star-k"></span>
              <span className="space-star star-l"></span>
            </div>

            <div className="sun-core"></div>
            <div className="asteroid-field">
              {Array.from({ length: 20 }).map((_, i) => (
                <div key={i} className="asteroid-mini" />
                ))}
                </div>

            <div className="orbit orbit-1">
              <div className="planet-track spin-slow">
                <div className="planet planet-1"></div>
              </div>
            </div>

            <div className="orbit orbit-2">
              <div className="planet-track spin-medium">
                <div className="planet planet-2"></div>
              </div>
            </div>

            <div className="orbit orbit-3">
              <div className="planet-track spin-fast">
                <div className="planet planet-3"></div>
              </div>
            </div>

            <div className="orbit orbit-4">
              <div className="planet-track spin-asteroid">
                <div className="asteroid-marker"></div>
              </div>
            </div>
              

            <div className="sector-card">
              <span className="sector-label">CURRENT SECTOR</span>
              <strong>Inner Solar Observation Zone</strong>
              <small>Tracking window active</small>
            </div>
          </div>

          <div className="stats-row">
            <div className="mini-stat">
              <span className="mini-stat-label">Tracked Objects</span>
              <strong>
                {
                [...myObservationHistory, ...publicObservationHistory].filter(
                  (item) => item.status === "OrbitCalculated"
                ).length
                }
                </strong>
            </div>
            
            <div className="mini-stat">
              <span className="mini-stat-label">My Uploads</span>
              <strong>{myObservationHistory.length}</strong>
            </div>
            <div className="mini-stat">
              <span className="mini-stat-label">Public Uploads</span>
              <strong>{publicObservationHistory.length}</strong>
            </div>
          </div>
        </section>

        <aside className="control-panel">
          <div className="glass-card upload-card">
            <div className="section-header compact">
              <span className="section-tag">Observations</span>
              <h3>Upload New File</h3>
            </div>

            <div className="visibility-box">
              <label className="visibility-label">Visibility</label>
              <select
                className="visibility-select"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as "private" | "public")}
              >
                <option value="private">Private</option>
                <option value="public">Public</option>
              </select>
            </div>

            <label className="upload-dropzone">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.csv"
                onChange={handleFileChange}
              />

              {selectedFile ? (
                <div className="upload-selected-state">
                  <div className="upload-selected-text">
                    <span className="upload-main">Selected file</span>
                    <span className="upload-file-name">{selectedFile.name}</span>
                    {uploadMessage && (
                      <span className="upload-success-message">{uploadMessage}</span>
                    )}
                  </div>

                  <button
                    type="button"
                    className="clear-file-btn"
                    onClick={(e) => {
                      e.preventDefault();
                      handleClearFile();
                    }}
                  >
                    ×
                  </button>
                </div>
              ) : (
                <>
                  <span className="upload-main">Drop JSON / CSV here</span>
                  <span className="upload-sub">or click to browse your files</span>
                </>
              )}
            </label>

            <button
              className="primary-action-btn"
              onClick={handleUpload}
              disabled={!selectedFile || isAnalyzing}
            >
              {isAnalyzing ? "Analyzing..." : "Upload Observations"}
            </button>
          </div>

          <div className="glass-card system-card">
            <div className="section-header compact">
              <span className="section-tag">System Status</span>
              <h3>Mission Snapshot</h3>
            </div>

            <div className="snapshot-row">
              <span>Database</span>
              <strong>Connected</strong>
            </div>
            <div className="snapshot-row">
              <span>Backend</span>
              <strong>Online</strong>
            </div>
            <div className="snapshot-row">
              <span>Upload Queue</span>
              <strong>{isAnalyzing ? "Processing" : "Idle"}</strong>
            </div>
            <div className="snapshot-row">
              <span>Prediction Engine</span>
              <strong>{isAnalyzing ? "Running" : selectedResult ? "Active" : "Standby"}</strong>
            </div>
          </div>
        </aside>

        <section className="history-panel glass-card">
          <div className="history-top">
            <div className="section-header compact">
              <span className="section-tag">
                {activeArchive === "my" ? "My Archive" : "Public Archive"}
              </span>
              <h3>
                {activeArchive === "my"
                  ? "My Observation History"
                  : "Shared Observation History"}
              </h3>
            </div>
          </div>

          <div className="archive-toggle">
            <button
              className={`archive-toggle-btn ${
                activeArchive === "my" ? "archive-toggle-btn-active" : ""
              }`}
              onClick={() => setActiveArchive("my")}
            >
              My Archive
            </button>

            <button
              className={`archive-toggle-btn ${
                activeArchive === "public" ? "archive-toggle-btn-active" : ""
              }`}
              onClick={() => setActiveArchive("public")}
            >
              Public Archive
            </button>
          </div>

          {activeArchive === "my"
            ? renderArchiveList(
                myObservationHistory,
                "No private or personal observations yet",
                "Upload your first observation file to see it here."
              )
            : renderArchiveList(
                publicObservationHistory,
                "No public observations yet",
                "Public observation files shared by users will appear here."
              )}

          {resultMessage && (
            <div className="history-error-text" style={{ marginTop: "16px" }}>
              {resultMessage}
            </div>
          )}
        </section>
      </main>

      {selectedResult && (
        <div className="orbit-modal-overlay">
          <div className="orbit-modal">
            <button
              className="orbit-modal-close"
              onClick={() => setSelectedResult(null)}
            >
              ×
            </button>

            <div className="orbit-modal-header">
              <span className="section-tag">Orbit Results</span>
              <h2>Calculated Orbital Elements</h2>
              <p>
                Results generated from the selected observation file using a custom
                iterative orbit fitting algorithm.
              </p>
            </div>

            <div className="orbit-modal-content">
              <div className="orbit-visual-column">
              <div className="orbit-modal-visual asteroid-orbit-visual">
  <div className="sun-core"></div>

  {(() => {
    const total = Math.max(selectedResult.predictions.data.length, 1);
    const safeIndex = Math.min(predictionIndex, total - 1);

    const asteroidAngle = (safeIndex / total) * 2 * Math.PI + 0.45;
    const orbitWidth = Math.min(
      430,
      260 + selectedResult.orbital.orbitalElements.a * 70
    );

    const orbitHeight = Math.max(
      130,
      orbitWidth * (1 - Math.min(selectedResult.orbital.orbitalElements.e, 0.75))
    );

    const asteroidA = orbitWidth / 2;
    const asteroidB = orbitHeight / 2;

    const asteroidX = Math.cos(asteroidAngle) * asteroidA;
    const asteroidY = Math.sin(asteroidAngle) * asteroidB;

    const earthAngle = (safeIndex / total) * 2 * Math.PI;
    const earthRadius = 122.5; // half of 245px from CSS

    const earthX = Math.cos(earthAngle) * earthRadius;
    const earthY = Math.sin(earthAngle) * earthRadius;

    return (
      <>
        <div
          className="computed-orbit-path"
          style={{
            width: `${orbitWidth}px`,
            height: `${orbitHeight}px`,
          }}
        />

        <div className="earth-orbit-path" />

        <div
          className="animated-earth"
          style={{
            transform: `translate(calc(-50% + ${earthX}px), calc(-50% + ${earthY}px))`,
          }}
        >
          <span className="earth-marker" title="Earth"></span>
        </div>

        <div
          className="animated-asteroid"
          style={{
            transform: `translate(calc(-50% + ${asteroidX}px), calc(-50% + ${asteroidY}px))`,
          }}
        >
          <span className="asteroid-core"></span>
        </div>
      </>
    );
  })()}
</div>

                <div className="orbit-time-control orbit-time-control-standalone">
                  <div className="orbit-time-header">
                    <span>Time Scale</span>
                    <strong>Day {predictionIndex + 1}</strong>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max={Math.max(selectedResult.predictions.data.length - 1, 0)}
                    value={predictionIndex}
                    onChange={(e) => setPredictionIndex(Number(e.target.value))}
                  />

                  <small>
                    {selectedResult.predictions.data[predictionIndex]
                      ? formatDate(selectedResult.predictions.data[predictionIndex].time)
                      : "No prediction selected"}
                  </small>
                </div>

                <div className="orbital-elements-grid orbit-elements-under-visual">
                  <div>
                    <span>a</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.a)}</strong>
                  </div>
                  <div>
                    <span>e</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.e)}</strong>
                  </div>
                  <div>
                    <span>Ω</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.Omega)}</strong>
                  </div>
                  <div>
                    <span>i</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.inc)}</strong>
                  </div>
                  <div>
                    <span>ω</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.omega)}</strong>
                  </div>
                  <div>
                    <span>M₀</span>
                    <strong>{formatNumber(selectedResult.orbital.orbitalElements.M0)}</strong>
                  </div>
                </div>
              </div>

              <div className="prediction-chart-card">
                <h4>RA / DEC Prediction Graph</h4>

                <ForecastCharts
                predictions={selectedResult.predictions.data}
                selectedIndex={predictionIndex}
                />

                <div className="results-grid results-under-chart">
                  <div className="result-card">
                    <span>RMS Error</span>
                    <strong>{formatNumber(selectedResult.orbital.rmsDeg, 4)}°</strong>
                  </div>

                  <div className="result-card">
                    <span>Observations</span>
                    <strong>{selectedResult.orbital.observationsCount}</strong>
                  </div>

                  <div className="result-card">
                    <span>Algorithm</span>
                    <strong>Custom Iterative Orbit Fitting</strong>
                  </div>
                </div>
              </div>

              <div className="orbit-modal-details">
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
