import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, Zap, Shield, Cpu, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface MousePosition {
  x: number;
  y: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

interface Feature {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  gradient: string;
}

export default function NeosilixLanding(): JSX.Element {
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState<number>(0);
  const [mousePos, setMousePos] = useState<MousePosition>({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const handleScroll = (): void => setScrollY(window.scrollY);
    const handleMouseMove = (e: MouseEvent): void => {
      setMousePos({
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: (e.clientY / window.innerHeight - 0.5) * 2
      });
    };

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('mousemove', handleMouseMove);

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

    const particles: Particle[] = Array.from({ length: 100 }, () => ({
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
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', setCanvasSize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  const features: Feature[] = [
    {
      icon: Zap,
      title: 'Lightning Speed',
      desc: 'Experience blazing-fast performance with our optimized architecture',
      gradient: 'from-violet-500 to-purple-600'
    },
    {
      icon: Shield,
      title: 'Security',
      desc: 'Military-grade encryption protecting your most valuable assets',
      gradient: 'from-fuchsia-500 to-pink-600'
    },
    {
      icon: Cpu,
      title: 'Neural Processing',
      desc: 'AI-powered systems that learn and adapt to your needs',
      gradient: 'from-purple-500 to-violet-600'
    }
  ];

  const techFeatures: string[] = [
    'Quantum-Ready Infrastructure',
    'Self-Healing Systems',
    'Zero-Latency Network'
  ];

  return (
    <div className="bg-black text-white min-h-screen overflow-x-hidden">
      <canvas ref={canvasRef} className="fixed inset-0 opacity-20 pointer-events-none" />

      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" />
       <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-fuchsia-600 rounded-full mix-blend-multiply opacity-30 animate-pulse" style={{ animationDelay: '2s' }} />
         </div>

      <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrollY > 50 ? 'bg-black/80 backdrop-blur-xl border-b border-white/10' : ''}`}>
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center gap-3">
              <div className="relative w-10 h-10">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg transform rotate-45" />
                <div className="absolute inset-1 bg-black rounded-lg transform rotate-45" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">N</span>
                </div>
              </div>
              <span className="text-2xl font-bold tracking-tight">NEOSILIX</span>
            </div>

            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">Features</a>
              <a href="#technology" className="text-sm text-gray-400 hover:text-white transition-colors">Technology</a>
              <a href="#about" className="text-sm text-gray-400 hover:text-white transition-colors">About</a>
              <button className="px-6 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-gray-100 transition-colors" onClick={() => navigate('/login')}>
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      <section className="relative min-h-screen flex items-center justify-center px-6 pt-20">
        <div className="max-w-7xl mx-auto w-full">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-full">
                <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
                <span className="text-xs uppercase tracking-wider text-gray-400">Next Generation Technology</span>
              </div>

              <h1 className="text-6xl lg:text-7xl xl:text-8xl font-bold leading-none">
                <span className="block text-white">The Future</span>
                <span className="block bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
                  of Innovation
                </span>
              </h1>

              <p className="text-xl text-gray-400 leading-relaxed max-w-xl">
                Experience breakthrough technology that redefines what's possible. 
                Neosilix delivers unparalleled performance, security, and Auto heals for your infrastructure.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <button className="group flex items-center justify-center gap-2 px-8 py-4 bg-white text-black rounded-lg font-semibold hover:bg-gray-100 transition-all" onClick={() => navigate('/login')}>
                  Start Your Journey with us
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-8 pt-8">
                <div>
                  <div className="text-3xl font-bold text-white">99.9%</div>
                  <div className="text-sm text-gray-500 mt-1">Uptime</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white">1M+</div>
                  <div className="text-sm text-gray-500 mt-1">Users</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white">50+</div>
                  <div className="text-sm text-gray-500 mt-1">Countries</div>
                </div>
              </div>
            </div>

            <div className="relative flex items-center justify-center h-[600px]">
              <div 
                className="relative w-80 h-80"
                style={{
                  transform: `perspective(1000px) rotateY(${mousePos.x * 5}deg) rotateX(${-mousePos.y * 5}deg)`,
                  transition: 'transform 0.1s ease-out'
                }}
              >
                <div className="absolute inset-0 border border-violet-500/30 rounded-full animate-spin" style={{ animationDuration: '20s' }} />
                <div className="absolute inset-8 border border-fuchsia-500/30 rounded-full animate-spin" style={{ animationDuration: '15s', animationDirection: 'reverse' }} />
                <div className="absolute inset-16 border border-purple-500/30 rounded-full animate-spin" style={{ animationDuration: '10s' }} />

                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="relative">
                    <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-fuchsia-600 rounded-3xl blur-3xl opacity-50" />
                    
                    <div className="relative w-40 h-40 bg-gradient-to-br from-violet-500 via-fuchsia-500 to-purple-600 rounded-3xl transform rotate-45 shadow-2xl">
                      <div className="absolute inset-3 bg-black rounded-2xl flex items-center justify-center">
                        <span className="text-5xl font-black bg-gradient-to-br from-violet-400 to-fuchsia-400 bg-clip-text text-transparent transform -rotate-45">
                          N
                        </span>
                      </div>
                    </div>

                    {[0, 1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className="absolute w-2 h-2 bg-gradient-to-br from-violet-400 to-fuchsia-400 rounded-full shadow-lg shadow-violet-500/50"
                        style={{
                          top: `${50 + Math.sin((i * Math.PI) / 3) * 80}%`,
                          left: `${50 + Math.cos((i * Math.PI) / 3) * 80}%`,
                          animation: 'float 3s ease-in-out infinite',
                          animationDelay: `${i * 0.5}s`
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
            <span className="text-xs text-gray-500 uppercase tracking-wider">Scroll to explore</span>
            <ChevronDown className="w-5 h-5 text-gray-500" />
          </div>
        </div>
      </section>

      <section id="features" className="relative py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl lg:text-6xl font-bold mb-6">
              <span className="text-white">Engineered for</span>
              <br />
              <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                Excellence
              </span>
            </h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Every detail meticulously crafted to deliver unprecedented performance and reliability
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <div
                key={i}
                className="group relative p-8 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl hover:bg-white/10 hover:border-white/20 transition-all duration-300"
              >
                <div className={`inline-flex p-4 bg-gradient-to-br ${feature.gradient} rounded-xl mb-6 group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3">{feature.title}</h3>
                <p className="text-gray-400 leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="technology" className="relative py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="relative h-96 rounded-3xl overflow-hidden bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 backdrop-blur-sm border border-white/10">
              {/*  Image */}
              <img
            src="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80"
  alt="Futuristic technology network"
  className="w-full h-full object-cover"
            />   
              {/* Optional overlay for better integration with design */}
              <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 mix-blend-overlay" />
            </div>

            <div className="space-y-6">
              <h2 className="text-5xl font-bold">
                <span className="text-white">Breakthrough</span>
                <br />
                <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                  Technology
                </span>
              </h2>
              <p className="text-xl text-gray-400 leading-relaxed">
                Built on cutting-edge architecture that pushes the boundaries of what's possible. 
                Our proprietary technology delivers performance that was once thought impossible.
              </p>
              <div className="space-y-4">
                {techFeatures.map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-violet-500 rounded-full" />
                    <span className="text-gray-300">{item}</span>
                  </div>
                ))}
              </div>
              <button className="group flex items-center gap-2 text-violet-400 hover:text-violet-300 transition-colors mt-8">
                Explore Technology
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="relative py-32 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="relative p-16 rounded-3xl overflow-hidden bg-gradient-to-br from-violet-600 to-fuchsia-600">
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMCAwIDAgMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS1vcGFjaXR5PSIwLjEiIHN0cm9rZS13aWR0aD0iMSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNncmlkKSIvPjwvc3ZnPg==')] opacity-30" />
            
            <div className="relative text-center">
              <h2 className="text-5xl font-bold mb-6">Ready to Transform?</h2>
              <p className="text-xl opacity-90 mb-10 max-w-2xl mx-auto">
                Join thousands of innovators who are already experiencing the future
              </p>
              <button className="px-10 py-5 bg-black text-white rounded-lg font-bold text-lg hover:bg-gray-900 transition-colors shadow-2xl" onClick={() => navigate('/login')}>
                Get Started Now
              </button>
            </div>
          </div>
        </div>
      </section>

      <footer className="relative py-12 px-6 border-t border-white/10">
        <div className="max-w-7xl mx-auto text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="relative w-8 h-8">
              <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg transform rotate-45" />
              <div className="absolute inset-1 bg-black rounded-lg transform rotate-45" />
            </div>
            <span className="text-xl font-bold">NEOSILIX</span>
          </div>
          <p className="text-gray-500">© 2025 Neosilix. All rights reserved.</p>
        </div>
      </footer>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translate(-50%, -50%) translateY(0); }
          50% { transform: translate(-50%, -50%) translateY(-10px); }
        }
      `}</style>
    </div>
  );
}
