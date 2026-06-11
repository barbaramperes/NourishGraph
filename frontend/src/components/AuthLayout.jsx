import { Leaf } from 'lucide-react'

export default function AuthLayout({ children }) {
    return (
        <div className="min-h-screen min-h-[100dvh] bg-base relative overflow-x-hidden overflow-y-auto">
            {/* Animated Background */}
            <div className="absolute inset-0">
                {/* Primary gradient orb - top left */}
                <div className="absolute top-[-30%] left-[-15%] w-[70%] h-[70%] rounded-full blur-[150px] animate-float"
                    style={{ background: 'radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, transparent 70%)' }} />

                {/* Secondary gradient orb - bottom right */}
                <div className="absolute bottom-[-25%] right-[-15%] w-[60%] h-[60%] rounded-full blur-[130px] animate-float"
                    style={{ background: 'radial-gradient(circle, rgba(5, 150, 105, 0.12) 0%, transparent 70%)', animationDelay: '-3s' }} />

                {/* Accent orb - center right */}
                <div className="absolute top-[30%] right-[10%] w-[40%] h-[40%] rounded-full blur-[100px] animate-float"
                    style={{ background: 'radial-gradient(circle, rgba(168, 85, 247, 0.08) 0%, transparent 70%)', animationDelay: '-5s' }} />

                {/* Subtle grid pattern */}
                <div className="absolute inset-0 opacity-[0.03]"
                    style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '80px 80px' }} />

                {/* Top glow line */}
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
            </div>

            {/* Content */}
            <div className="relative z-10 min-h-screen min-h-[100dvh] flex items-center justify-center p-4 sm:p-6 pb-8 sm:pb-6">
                <div className="w-full max-w-md">
                    {/* Main Card */}
                    <div className="animate-slideUp">
                        <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden"
                            style={{
                                background: 'var(--color-bg-card)',
                                boxShadow: '0 40px 80px rgba(0, 0, 0, 0.2), 0 0 120px rgba(16, 185, 129, 0.03)',
                                border: '1px solid var(--color-border)'
                            }}>

                            {/* Top accent line */}
                            <div className="absolute top-0 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" />

                            {/* Premium Header */}
                            <div className="relative text-center pt-8 sm:pt-12 pb-6 sm:pb-8 px-6 sm:px-8">
                                {/* Background glow */}
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full blur-[80px]"
                                    style={{ background: 'radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, transparent 70%)' }} />

                                <div className="relative">
                                    {/* Logo */}
                                    <div className="inline-flex flex-col items-center gap-4 sm:gap-5">
                                        <div className="relative group">
                                            {/* Outer glow ring */}
                                            <div className="absolute -inset-3 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                                style={{ background: 'radial-gradient(circle, rgba(16, 185, 129, 0.3) 0%, transparent 70%)', filter: 'blur(20px)' }} />

                                            {/* Logo container */}
                                            <div className="relative w-16 h-16 sm:w-[72px] sm:h-[72px] rounded-xl sm:rounded-2xl flex items-center justify-center transform hover:scale-105 transition-all duration-300"
                                                style={{
                                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 50%, #047857 100%)',
                                                    boxShadow: '0 20px 40px rgba(16, 185, 129, 0.3), inset 0 1px 0 rgba(255,255,255,0.2)'
                                                }}>
                                                <Leaf className="w-8 h-8 sm:w-9 sm:h-9" style={{ color: '#ffffff' }} />
                                            </div>
                                        </div>

                                        {/* Brand name */}
                                        <div className="flex items-baseline gap-0.5">
                                            <span className="text-2xl sm:text-3xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
                                                Nourish
                                            </span>
                                            <span className="text-2xl sm:text-3xl font-bold tracking-tight"
                                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                                Graph
                                            </span>
                                        </div>
                                    </div>

                                    {/* Tagline */}
                                    <p className="text-zinc-500 text-xs sm:text-sm font-medium tracking-wide mt-2 sm:mt-3">
                                        AI-Powered Nutrition Intelligence
                                    </p>
                                </div>
                            </div>

                            {/* Divider */}
                            <div className="mx-6 sm:mx-8 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

                            {/* Body */}
                            <div className="p-5 sm:p-8 pt-5 sm:pt-6">
                                {children}
                            </div>
                        </div>
                    </div>

                    {/* Footer intentionally removed */}
                </div>
            </div>
        </div>
    )
}
