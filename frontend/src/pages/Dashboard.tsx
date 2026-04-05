import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import "../App.css";

type ObservationItem = {
  fileName: string;
  uploadedBy: string;
  uploadedAt: string;
  count: number;
  status: string;
  invalidReason?: string;
  visibility: "private" | "public";
};

function Dashboard() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [myObservationHistory, setMyObservationHistory] = useState<ObservationItem[]>([]);
  const [publicObservationHistory, setPublicObservationHistory] = useState<ObservationItem[]>([]);

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
    if (!selectedFile) {
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("uploadedBy", loggedInUser);
    formData.append("visibility", visibility);

    try {
      const response = await fetch("http://127.0.0.1:8000/observations/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        if (data.status === "Validated") {
          setUploadMessage(`Uploaded successfully (${visibility})`);
        } else {
          setUploadMessage(data.invalidReason || "File uploaded but failed validation");
        }

        await refreshArchives();
      } else {
        setUploadMessage(data.message || "Upload failed");
      }
    } catch (error) {
      setUploadMessage("Server connection error");
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const renderStatusClass = (status: string) => {
    if (status === "Validated") return "status-validated";
    if (status === "Invalid") return "status-invalid";
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

            <span className={`status-badge ${renderStatusClass(item.status)}`}>
              {item.status}
            </span>
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
              <strong>12</strong>
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
              disabled={!selectedFile}
            >
              Upload Observations
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
              <strong>Idle</strong>
            </div>
            <div className="snapshot-row">
              <span>Prediction Engine</span>
              <strong>Standby</strong>
            </div>
          </div>
        </aside>

        <section className="history-panel glass-card">
          <div className="history-top">
            <div className="section-header compact">
              <span className="section-tag">My Archive</span>
              <h3>My Observation History</h3>
            </div>
          </div>

          {renderArchiveList(
            myObservationHistory,
            "No private or personal observations yet",
            "Upload your first observation file to see it here."
          )}
        </section>

        <section className="history-panel glass-card">
          <div className="history-top">
            <div className="section-header compact">
              <span className="section-tag">Public Archive</span>
              <h3>Shared Observation History</h3>
            </div>
          </div>

          {renderArchiveList(
            publicObservationHistory,
            "No public observations yet",
            "Public observation files shared by users will appear here."
          )}
        </section>
      </main>
    </div>
  );
}

export default Dashboard;