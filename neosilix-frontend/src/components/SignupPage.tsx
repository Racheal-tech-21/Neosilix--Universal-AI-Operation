import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, Mail, Lock, Eye, EyeOff } from 'lucide-react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const setCanvasSize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    setCanvasSize();
    window.addEventListener('resize', setCanvasSize);

    const particles: Particle[] = Array.from({ length: 50 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 1.5 + 0.5
    }));

    let animationId: number;
    const animate = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p, i) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(139, 92, 246, 0.6)';
        ctx.fill();

        particles.slice(i + 1).forEach(p2 => {
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(139, 92, 246, ${0.15 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('resize', setCanvasSize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  const handleSubmit = async (e: React.MouseEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    try {
      const res = await fetch("http://localhost:5000/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        throw new Error("Signup failed");
      }

      setSuccess("Account created successfully! Redirecting...");
      setTimeout(() => window.location.href = "/login", 1500);
    } catch (err: any) {
      setError(err.message || "Signup failed");
    }
  };

  return (
    <div className="bg-black text-white min-h-screen overflow-hidden relative">
      <canvas ref={canvasRef} className="fixed inset-0 opacity-20 pointer-events-none" />

      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-fuchsia-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" style={{ animationDelay: '1s' }} />
        </div>
        
      <nav className="fixed top-0 w-full z-50 bg-black/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <a href="/" className="flex items-center gap-3">
              <div className="relative w-10 h-10">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg transform rotate-45" />
                <div className="absolute inset-1 bg-black rounded-lg transform rotate-45" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">N</span>
                </div>
              </div>
              <span className="text-2xl font-bold tracking-tight">NEOSILIX</span>
            </a>
          </div>
        </div>
      </nav>

      <div className="relative min-h-screen flex items-center justify-center px-6 pt-20">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-full mb-6">
              <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
              <span className="text-xs uppercase tracking-wider text-gray-400">Join the Future</span>
            </div>
            
            <h1 className="text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
                Create Account
              </span>
            </h1>
            <p className="text-gray-400">Start your journey with Neosilix</p>
          </div>

          <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-red-400 text-sm text-center">{error}</p>
              </div>
            )}
            
            {success && (
              <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                <p className="text-green-400 text-sm text-center">{success}</p>
              </div>
            )}

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <button
                onClick={handleSubmit}
                className="group w-full flex items-center justify-center gap-2 py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 rounded-xl font-semibold text-white transition-all shadow-lg shadow-violet-500/25"
              >
                Create Account
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            <div className="mt-6 text-center">
              <p className="text-gray-400 text-sm">
                Already have an account?{" "}
                <a href="/login" className="text-violet-400 hover:text-violet-300 font-medium transition-colors">
                  Sign in
                </a>
              </p>
            </div>
          </div>

          <p className="text-center text-xs text-gray-500 mt-6">
            By creating an account, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
