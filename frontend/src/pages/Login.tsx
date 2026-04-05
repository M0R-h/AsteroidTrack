import { useMemo, useState } from "react"
import { User, Lock, Eye, EyeOff } from "lucide-react"
import { useNavigate } from "react-router-dom"

function Login() {
  const navigate = useNavigate()

  const [loginData, setLoginData] = useState({
    username: "",
    password: "",
  })

  const [message, setMessage] = useState("")
  const [showLoginPassword, setShowLoginPassword] = useState(false)

  const stars = useMemo(() => {
    return Array.from({ length: 60 }, (_, i) => ({
      id: i,
      top: `${Math.random() * 100}%`,
      left: `${Math.random() * 100}%`,
      size: `${1 + Math.random() * 2}px`,
      delay: `${Math.random() * 4}s`,
      duration: `${2 + Math.random() * 3}s`,
    }))
  }, [])

  const meteors = useMemo(() => {
    const count = 9

    return Array.from({ length: count }, (_, i) => ({
      id: i,
      top: `${Math.random() * 60}%`,
      left: `${(i / count) * 100 + Math.random() * 10}%`,
      delay: `${Math.random() * 8}s`,
      duration: `${4 + Math.random() * 4}s`,
    }))
  }, [])

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!loginData.username || !loginData.password) {
      setMessage("Please fill in all fields")
      return
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: loginData.username,
          password: loginData.password,
        }),
      })

      const data = await response.json()
      setMessage(data.message)

      if (data.message === "Login successful") {
        localStorage.setItem(
          "asteroidtrack_user",
          JSON.stringify({
            username: data.username,
            email: data.email,
          })
        )

        navigate("/dashboard")
      }
    } catch (error) {
      setMessage("Server connection error")
    }
  }

  return (
    <div className="page">
      <div className="space-background">
        {stars.map((star) => (
          <span
            key={star.id}
            className="star"
            style={{
              top: star.top,
              left: star.left,
              width: star.size,
              height: star.size,
              animationDelay: star.delay,
              animationDuration: star.duration,
            }}
          />
        ))}

        {meteors.map((meteor) => (
          <span
            key={meteor.id}
            className="meteor"
            style={{
              top: meteor.top,
              left: meteor.left,
              animationDelay: meteor.delay,
              animationDuration: meteor.duration,
            }}
          />
        ))}

        <div className="nebula nebula-1"></div>
        <div className="nebula nebula-2"></div>
      </div>

      <div className="auth-shell">
        <div className="auth-left">
          <div className="brand-panel">
            <div className="brand-badge">AsteroidTrack</div>

            <h1 className="brand-title">
              Track the sky.
              <br />
              Predict the orbit.
            </h1>

            <p className="brand-description">
              A platform for asteroid orbit analysis, prediction, and
              computation based on astronomical observations, Keplerian
              modeling, and orbit fitting algorithms.
            </p>

            <div className="info-grid">
              <div className="info-card">
                <span>Observations</span>
                <strong>RA / DEC / Time</strong>
              </div>

              <div className="info-card">
                <span>Orbit Computation</span>
                <strong>Kepler + Orbit Fit</strong>
              </div>

              <div className="info-card">
                <span>Output</span>
                <strong>RMS + Orbital Elements</strong>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-right">
          <div className="form-card">
            <div className="form-header">
              <h2>Login</h2>
              <p>Sign in to continue to AsteroidTrack</p>
            </div>

            <form className="form" onSubmit={handleLoginSubmit}>
              <div className="field">
                <label>Username</label>

                <div className="input-wrapper">
                  <User size={18} className="input-icon-left" />

                  <input
                    type="text"
                    required
                    placeholder="Enter username"
                    value={loginData.username}
                    onChange={(e) =>
                      setLoginData({
                        ...loginData,
                        username: e.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="field">
                <label>Password</label>

                <div className="input-wrapper">
                  <Lock size={18} className="input-icon-left" />

                  <input
                    type={showLoginPassword ? "text" : "password"}
                    placeholder="Enter password"
                    value={loginData.password}
                    onChange={(e) =>
                      setLoginData({
                        ...loginData,
                        password: e.target.value,
                      })
                    }
                  />

                  <button
                    type="button"
                    className="eye-btn"
                    onClick={() => setShowLoginPassword(!showLoginPassword)}
                  >
                    {showLoginPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="primary-btn">
                Login
              </button>
            </form>

            <p className="switch-text">
              Don&apos;t have an account?{" "}
              <button
                className="link-btn"
                type="button"
                onClick={() => {
                  setMessage("")
                  navigate("/register")
                }}
              >
                Register
              </button>
            </p>

            {message && <div className="message-box">{message}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login