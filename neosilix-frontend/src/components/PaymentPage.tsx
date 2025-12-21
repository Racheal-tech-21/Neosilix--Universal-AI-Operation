import React, { useState, useEffect, useRef } from 'react';
import { Check, Zap, Shield, Cpu, Crown, ArrowRight } from 'lucide-react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

export default function PaymentPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('pro');
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

  const handleUpgrade = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const token = 'your-token-here'; // Replace with actual token retrieval
      const res = await fetch('http://localhost:4000/upgrade', {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ plan: selectedPlan })
      });

      if (!res.ok) throw new Error('Upgrade failed');

      setSuccess('Plan upgraded successfully! Redirecting...');
      setTimeout(() => window.location.href = '/', 1500);
    } catch (err: any) {
      setError(err.message || 'Upgrade failed');
    } finally {
      setLoading(false);
    }
  };

  const plans = [
    {
      id: 'pro',
      name: 'Pro',
      price: '$49',
      period: '/month',
      icon: Zap,
      gradient: 'from-violet-500 to-purple-600',
      features: [
        'Lightning-fast performance',
        'Advanced analytics',
        'Priority support',
        'Custom integrations',
        '99.9% uptime SLA'
      ]
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: '$199',
      period: '/month',
      icon: Crown,
      gradient: 'from-fuchsia-500 to-pink-600',
      popular: true,
      features: [
        'Everything in Pro',
        'Dedicated account manager',
        'Custom AI models',
        'White-label solution',
        '99.99% uptime SLA',
        'Advanced security'
      ]
    }
  ];

  return (
    <div className="bg-black text-white min-h-screen overflow-hidden relative">
      <canvas ref={canvasRef} className="fixed inset-0 opacity-20 pointer-events-none" />

      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600 rounded-full mix-blend-multiply filter blur-[128px] opacity-30 animate-pulse" />
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-fuchsia-600 rounded-full mix-blend-multiply filter blur-[128px] opacity-30 animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-[128px] opacity-30 animate-pulse" style={{ animationDelay: '2s' }} />
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

      <div className="relative min-h-screen flex items-center justify-center px-6 py-32">
        <div className="max-w-6xl mx-auto w-full">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-full mb-6">
              <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
              <span className="text-xs uppercase tracking-wider text-gray-400">Unlock Full Potential</span>
            </div>
            
            <h1 className="text-6xl font-bold mb-6">
              <span className="block text-white mb-2">Upgrade Your</span>
              <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
                Experience
              </span>
            </h1>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              Your trial has expired. Choose a plan that fits your needs and continue revolutionizing your workflow
            </p>
          </div>

          {error && (
            <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl max-w-2xl mx-auto">
              <p className="text-red-400 text-center">{error}</p>
            </div>
          )}
          
          {success && (
            <div className="mb-8 p-4 bg-green-500/10 border border-green-500/20 rounded-xl max-w-2xl mx-auto">
              <p className="text-green-400 text-center">{success}</p>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto mb-12">
            {plans.map((plan) => (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`relative p-8 rounded-3xl cursor-pointer transition-all duration-300 ${
                  selectedPlan === plan.id
                    ? 'bg-white/10 border-2 border-violet-500 shadow-2xl shadow-violet-500/25 scale-105'
                    : 'bg-white/5 border border-white/10 hover:bg-white/8'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-full text-xs font-semibold uppercase tracking-wider">
                    Most Popular
                  </div>
                )}

                <div className={`inline-flex p-4 bg-gradient-to-br ${plan.gradient} rounded-xl mb-6`}>
                  <plan.icon className="w-8 h-8 text-white" />
                </div>

                <h3 className="text-3xl font-bold mb-2">{plan.name}</h3>
                
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-5xl font-bold bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                    {plan.price}
                  </span>
                  <span className="text-gray-500">{plan.period}</span>
                </div>

                <div className="space-y-4 mb-8">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start gap-3">
                      <div className="mt-1">
                        <Check className="w-5 h-5 text-violet-400" />
                      </div>
                      <span className="text-gray-300">{feature}</span>
                    </div>
                  ))}
                </div>

                {selectedPlan === plan.id && (
                  <div className="absolute top-4 right-4">
                    <div className="w-6 h-6 bg-violet-500 rounded-full flex items-center justify-center">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="text-center">
            <button
              onClick={handleUpgrade}
              disabled={loading}
              className={`group inline-flex items-center gap-2 px-12 py-5 rounded-xl font-bold text-lg transition-all shadow-lg ${
                loading
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 shadow-violet-500/25'
              }`}
            >
              {loading ? 'Processing...' : 'Upgrade Now'}
              {!loading && <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
            </button>
            
            <p className="text-gray-500 text-sm mt-6">
              30-day money-back guarantee • Cancel anytime • No hidden fees
            </p>
          </div>

          <div className="mt-16 p-8 bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl max-w-3xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div>
                <Shield className="w-8 h-8 text-violet-400 mx-auto mb-3" />
                <h4 className="font-semibold mb-2">Secure Payment</h4>
                <p className="text-sm text-gray-400">Bank-level encryption</p>
              </div>
              <div>
                <Cpu className="w-8 h-8 text-fuchsia-400 mx-auto mb-3" />
                <h4 className="font-semibold mb-2">Instant Access</h4>
                <p className="text-sm text-gray-400">Activated immediately</p>
              </div>
              <div>
                <Zap className="w-8 h-8 text-purple-400 mx-auto mb-3" />
                <h4 className="font-semibold mb-2">24/7 Support</h4>
                <p className="text-sm text-gray-400">Always here to help</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
