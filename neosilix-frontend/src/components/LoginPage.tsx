import { useState, FormEvent, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../utils/auth";
import { Mail, Lock, Eye, EyeOff, ArrowRight, CreditCard, Calendar, Zap } from "lucide-react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

interface User {
  id: string;
  email: string;
  plan: string;
  trial_ends?: string;
  is_admin?: boolean;
  role?: string;
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showTrialExpiredModal, setShowTrialExpiredModal] = useState(false);
  const [userData, setUserData] = useState<User | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent): void => {
      setMousePos({
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: (e.clientY / window.innerHeight - 0.5) * 2
      });
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Canvas particle system
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const setCanvasSize = (): void => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    setCanvasSize();
    window.addEventListener('resize', setCanvasSize);

    const particles: Particle[] = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 1.5 + 0.5
    }));

    let animationId: number;
    const animate = (): void => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p, i) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(139, 92, 246, 0.5)';
        ctx.fill();

        particles.slice(i + 1).forEach(p2 => {
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(139, 92, 246, ${0.1 * (1 - dist / 100)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', setCanvasSize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  const checkTrialExpired = (user: User): boolean => {
    if (user.plan !== "trial") return false;
    if (!user.trial_ends) return false;
    
    const trialEnds = new Date(user.trial_ends);
    const now = new Date();
    return trialEnds < now;
  };

  // Update the handleLogin function:
const handleLogin = async (e: FormEvent) => {
  e.preventDefault();
  setLoading(true);
  setError("");
  setShowTrialExpiredModal(false);

  try {
    // REAL API CALL
    const res = await fetch("http://localhost:5000/auth/login", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.error || "Login failed");
    }

    const { token, user } = await res.json();

    if (!token || !user) throw new Error("Invalid server response");

    // Store auth data
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));

    const isAdmin = user.is_admin || user.role === "admin";
    
    // Only check trial for non-admin users
    if (!isAdmin && user.plan === "trial" && checkTrialExpired(user)) {
      setUserData(user);
      setShowTrialExpiredModal(true);
      setLoading(false);
      return;
    }

    // Proceed with normal login flow if trial is not expired or user is admin
    await handleSuccessfulLogin(token, user);

  } catch (err: any) {
    setError(err.message || "Login failed");
    setLoading(false);
  }
};

  const handleSuccessfulLogin = async (token: string, user: User) => {
    try {
      // Simulate dashboard API call
      await new Promise(resolve => setTimeout(resolve, 500));
             if (user.is_admin || user.role === "admin") {
        navigate("/dashboard/admin");
      } else {
        navigate("/");
      }
    } catch (err) {
      console.error("Dashboard fetch failed:", err);
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgradeNow = () => {
    if (!userData) return;
    
    // Store user data for payment page
    sessionStorage.setItem('upgradeUser', JSON.stringify({
      id: userData.id,
      email: userData.email,
      currentPlan: userData.plan,
      trialEnded: userData.trial_ends
    }));
    
    // Store token for API calls
    const token = localStorage.getItem('token');
    if (token) {
      sessionStorage.setItem('paymentToken', token);
    }
    
    // Navigate to payment page
    setShowTrialExpiredModal(false);
    navigate("/payment");
  };

  const handleContactSupport = () => {
    window.open('mailto:support@neosilix.com?subject=Trial%20Extension%20Request', '_blank');
    setShowTrialExpiredModal(false);
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6 overflow-hidden relative">
      {/* Animated Canvas Background */}
      <canvas ref={canvasRef} className="fixed inset-0 opacity-20 pointer-events-none" />

      {/* Background Gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-fuchsia-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* Main Content */}
      <div className="relative z-10 w-full max-w-6xl grid lg:grid-cols-2 gap-12 items-center">
        
        {/* Left Side - Branding */}
        <div className="hidden lg:block space-y-8">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg transform rotate-45" />
              <div className="absolute inset-1 bg-black rounded-lg transform rotate-45" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xl font-bold bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">N</span>
              </div>
            </div>
            <span className="text-3xl font-bold tracking-tight">NEOSILIX</span>
          </div>

          <div>
            <h1 className="text-6xl font-bold mb-6 leading-tight">
              <span className="block text-white">Welcome</span>
              <span className="block bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
                Back
              </span>
            </h1>
            <p className="text-xl text-gray-400 leading-relaxed">
              Access your command center and continue pushing the boundaries of innovation.
            </p>
          </div>

          {/* 3D Logo Display */}
          <div className="relative flex items-center justify-center h-64">
            <div 
              className="relative w-48 h-48"
              style={{
                transform: `perspective(1000px) rotateY(${mousePos.x * 8}deg) rotateX(${-mousePos.y * 8}deg)`,
                transition: 'transform 0.1s ease-out'
              }}
            >
              <div className="absolute inset-0 border border-violet-500/30 rounded-full animate-spin" style={{ animationDuration: '20s' }} />
              <div className="absolute inset-6 border border-fuchsia-500/30 rounded-full animate-spin" style={{ animationDuration: '15s', animationDirection: 'reverse' }} />

              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-fuchsia-600 rounded-2xl blur-2xl opacity-50" />
                  
                  <div className="relative w-24 h-24 bg-gradient-to-br from-violet-500 via-fuchsia-500 to-purple-600 rounded-2xl transform rotate-45 shadow-2xl">
                    <div className="absolute inset-2 bg-black rounded-xl flex items-center justify-center">
                      <span className="text-3xl font-black bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent transform -rotate-45">
                        N
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Login Form */}
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 rounded-3xl blur-xl" />
          
          <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 lg:p-12 shadow-2xl">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <div className="relative w-10 h-10">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg transform rotate-45" />
                <div className="absolute inset-1 bg-black rounded-lg transform rotate-45" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">N</span>
                </div>
              </div>
              <span className="text-2xl font-bold">NEOSILIX</span>
            </div>

            <div className="mb-8">
              <h2 className="text-3xl font-bold mb-2">Sign In</h2>
              <p className="text-gray-400">Enter your credentials to continue</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-xl">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-6">
              {/* Email Field */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2 text-gray-300">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                    placeholder="you@example.com"
                    required
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium mb-2 text-gray-300">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-12 pr-12 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="group w-full py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-violet-500/50 transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Signing In...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>

              {/* Sign Up Link */}
              <div className="text-center pt-4">
                <p className="text-gray-400">
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => navigate('/signup')}
                    className="text-violet-400 hover:text-violet-300 font-medium transition-colors"
                  >
                    Sign up
                  </button>
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Trial Expired Modal - Fixed positioning and z-index */}
      {showTrialExpiredModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/80 backdrop-blur-sm z-50 p-4">
          <div className="relative w-full max-w-md mx-auto">
            <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 rounded-3xl blur-xl" />
            
            <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-600 to-orange-600 rounded-2xl mb-4">
                  <Calendar className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-2">Trial Expired</h2>
                <p className="text-gray-400 mb-4">
                  Your free trial has ended. Upgrade to continue using Neosilix.
                </p>
                
                <div className="bg-white/5 rounded-xl p-4 mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-400">Current Plan</span>
                    <span className="text-amber-400 font-semibold">Trial</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Status</span>
                    <span className="text-red-400 font-semibold">Expired</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-gradient-to-r from-violet-600/20 to-fuchsia-600/20 border border-violet-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Zap className="w-5 h-5 text-violet-400" />
                    <h3 className="font-semibold text-white">Premium Features</h3>
                  </div>
                  <ul className="text-sm text-gray-300 space-y-1">
                    <li>• Full access to all features</li>
                    <li>• Priority support</li>
                    <li>• Advanced analytics</li>
                    <li>• Unlimited projects</li>
                  </ul>
                </div>

                <button
                  onClick={handleUpgradeNow}
                  className="w-full py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-violet-500/50 transition-all duration-300 hover:scale-[1.02] flex items-center justify-center gap-2"
                >
                  <CreditCard className="w-5 h-5" />
                  <span>Upgrade Now</span>
                  <ArrowRight className="w-5 h-5" />
                </button>

                <button
                  onClick={handleContactSupport}
                  className="w-full py-3 bg-white/5 border border-white/10 rounded-xl font-medium hover:bg-white/10 transition-all"
                >
                  Contact Support
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 p-4 text-center text-gray-500 text-sm border-t border-white/10 bg-black/50 backdrop-blur-sm z-40">
        © {new Date().getFullYear()} Neosilix. All rights reserved.
      </footer>
    </div>
  );
}
