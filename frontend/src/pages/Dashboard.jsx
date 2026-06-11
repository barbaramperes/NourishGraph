import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { getMacroGoals, getDietInfo, calculateCalorieGoal } from '../utils/macroCalculations'
import {
    ArrowRight, Flame, Drumstick, Wheat, Droplets,
    User, Activity, Scale, Brain, Sunrise, Sun, Moon,
    TrendingDown, Dumbbell, ChevronRight, Sparkles,
    TrendingUp, Utensils, Lightbulb, Plus, MessageCircle, Target,
    Heart, Zap, Calendar, Award, BookOpen, BarChart3, Ruler,
    // Diet icons
    Leaf, Fish, Egg, Apple, Salad, Beef, CircleOff, Cookie
} from 'lucide-react'

function calculateBMI(weight, height) {
    if (!weight || !height) return null
    const heightM = height / 100
    return (weight / (heightM * heightM)).toFixed(1)
}

function getBMICategory(bmi) {
    if (!bmi) return { label: '--', color: '#6B7280' }
    const val = parseFloat(bmi)
    if (val < 18.5) return { label: 'Underweight', color: '#F59E0B' }
    if (val < 25) return { label: 'Healthy', color: '#10B981' }
    if (val < 30) return { label: 'Overweight', color: '#F59E0B' }
    return { label: 'Obese', color: '#EF4444' }
}

const goalConfig = {
    'lose_weight': { label: 'Lose Weight', Icon: TrendingDown, color: '#F59E0B', gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' },
    'maintain': { label: 'Maintain', Icon: Scale, color: '#10B981', gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' },
    'gain_muscle': { label: 'Build Muscle', Icon: Dumbbell, color: '#8B5CF6', gradient: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)' }
}

const dietConfig = {
    'keto': { label: 'Ketogenic', color: '#8B5CF6', tip: 'Keep carbs under 50g daily', Icon: Egg },
    'mediterranean': { label: 'Mediterranean', color: '#10B981', tip: 'Focus on olive oil & fish', Icon: Fish },
    'vegetarian': { label: 'Vegetarian', color: '#22C55E', tip: 'Combine legumes with grains', Icon: Salad },
    'vegan': { label: 'Vegan', color: '#16A34A', tip: 'Ensure B12 supplementation', Icon: Leaf },
    'paleo': { label: 'Paleo', color: '#D97706', tip: 'Avoid processed foods', Icon: Beef },
    'carnivore': { label: 'Carnivore', color: '#DC2626', tip: 'Focus on fatty cuts', Icon: Beef },
    'low-carb': { label: 'Low Carb', color: '#0EA5E9', tip: 'Keep carbs under 100g', Icon: Egg },
    'pescatarian': { label: 'Pescatarian', color: '#0891B2', tip: 'Fish is your main protein', Icon: Fish },
    'gluten-free': { label: 'Gluten-Free', color: '#7C3AED', tip: 'Check labels carefully', Icon: CircleOff },
    'dairy-free': { label: 'Dairy-Free', color: '#EC4899', tip: 'Use plant-based alternatives', Icon: CircleOff }
}

const defaultDiet = { label: 'Balanced', color: '#10B981', tip: 'Eat a variety of whole foods', Icon: Apple }

// Animated progress ring for macros
function MacroProgress({ value, max, color, icon: Icon, label, size = 'md' }) {
    const radius = size === 'lg' ? 40 : 32
    const strokeWidth = size === 'lg' ? 6 : 5
    const circumference = 2 * Math.PI * radius
    const progress = max > 0 ? Math.min((value / max) * 100, 100) : 0
    const offset = circumference - (progress / 100) * circumference

    return (
        <div className="flex flex-col items-center">
            <div className="relative" style={{ width: radius * 2 + 16, height: radius * 2 + 16 }}>
                <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${(radius + 8) * 2} ${(radius + 8) * 2}`}>
                    {/* Background circle */}
                    <circle
                        cx={radius + 8}
                        cy={radius + 8}
                        r={radius}
                        stroke="var(--color-border)"
                        strokeWidth={strokeWidth}
                        fill="none"
                    />
                    {/* Progress circle */}
                    <circle
                        cx={radius + 8}
                        cy={radius + 8}
                        r={radius}
                        stroke={color}
                        strokeWidth={strokeWidth}
                        fill="none"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        className="transition-all duration-1000 ease-out"
                        style={{ filter: `drop-shadow(0 0 6px ${color}50)` }}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <Icon className={size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'} style={{ color }} />
                    <span className={`font-bold mt-0.5 ${size === 'lg' ? 'text-sm' : 'text-xs'}`} style={{ color: 'var(--color-text-primary)' }}>
                        {value}g
                    </span>
                </div>
            </div>
            <span className="text-xs font-medium mt-2" style={{ color: 'var(--color-text-muted)' }}>{label}</span>
        </div>
    )
}

// Stat card with gradient accent
function StatCard({ icon: Icon, value, label, sublabel, color, gradient }) {
    return (
        <div className="relative overflow-hidden rounded-xl sm:rounded-2xl p-3 sm:p-5 transition-all duration-300 hover:translate-y-[-2px] hover:shadow-xl group"
            style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
            {/* Gradient accent */}
            <div className="absolute top-0 left-0 right-0 h-1 opacity-80" style={{ background: gradient || color }} />

            <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: 'var(--color-text-muted)' }}>
                        {label}
                    </p>
                    <p className="text-lg sm:text-2xl font-bold truncate" style={{ color: 'var(--color-text-primary)' }}>
                        {value || '--'}
                    </p>
                    {sublabel && (
                        <p className="text-[10px] sm:text-xs font-semibold mt-0.5" style={{ color }}>
                            {sublabel}
                        </p>
                    )}
                </div>
                <div className="w-9 h-9 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl flex items-center justify-center flex-shrink-0 ml-2 transition-transform group-hover:scale-110"
                    style={{ background: color, boxShadow: `0 4px 12px ${color}40` }}>
                    <Icon className="w-4 h-4 sm:w-6 sm:h-6" style={{ color: '#ffffff' }} />
                </div>
            </div>
        </div>
    )
}

// Weekly progress tracker
function WeeklyProgress() {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    const today = new Date().getDay()
    const adjustedToday = today === 0 ? 6 : today - 1

    return (
        <div className="rounded-xl sm:rounded-2xl p-4 sm:p-5" style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#10B98115' }}>
                        <Calendar className="w-4 h-4" style={{ color: '#10B981' }} />
                    </div>
                    <div>
                        <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Weekly Progress</span>
                        <p className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>{adjustedToday + 1} of 7 days completed</p>
                    </div>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full" style={{ background: '#10B98115' }}>
                    <Zap className="w-3.5 h-3.5" style={{ color: '#10B981' }} />
                    <span className="text-xs font-bold" style={{ color: '#10B981' }}>{adjustedToday + 1} day streak</span>
                </div>
            </div>

            <div className="flex items-center justify-between gap-1">
                {days.map((day, i) => {
                    const isPast = i < adjustedToday
                    const isToday = i === adjustedToday
                    const isFuture = i > adjustedToday

                    return (
                        <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
                            <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-muted)' }}>{day}</span>
                            <div
                                className={`w-full aspect-square max-w-[36px] rounded-xl flex items-center justify-center text-xs font-bold transition-all ${isToday ? 'ring-2 ring-offset-2' : ''}`}
                                style={{
                                    background: isPast ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
                                        : isToday ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
                                            : 'var(--color-bg-tertiary)',
                                    color: isPast || isToday ? '#fff' : 'var(--color-text-muted)',
                                    '--tw-ring-color': '#10B981',
                                    '--tw-ring-offset-color': 'var(--color-bg-elevated)',
                                    boxShadow: isPast || isToday ? '0 4px 12px rgba(16, 185, 129, 0.3)' : 'none'
                                }}
                            >
                                {isPast ? '✓' : isToday ? '●' : ''}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

// Quick action button - icon is white when gradient is set
function QuickAction({ to, icon: Icon, label, color, gradient }) {
    return (
        <Link to={to} className="flex flex-col items-center gap-2 p-4 rounded-xl transition-all hover:scale-105 hover:shadow-lg group"
            style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
            <div className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
                style={{ background: gradient || `${color}15` }}>
                <Icon className="w-6 h-6" style={{ color: gradient ? '#ffffff' : color }} />
            </div>
            <span className="text-xs font-semibold text-center" style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
        </Link>
    )
}

export default function Dashboard() {
    const { profile, loadProfile } = useAppStore()
    const [greeting, setGreeting] = useState('')
    const [TimeIcon, setTimeIcon] = useState(() => Sun)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const load = async () => {
            setIsLoading(true)
            await loadProfile()
            setIsLoading(false)
        }
        load()
    }, [loadProfile])

    useEffect(() => {
        const hour = new Date().getHours()
        if (hour < 12) { setGreeting('Good morning'); setTimeIcon(() => Sunrise) }
        else if (hour < 17) { setGreeting('Good afternoon'); setTimeIcon(() => Sun) }
        else { setGreeting('Good evening'); setTimeIcon(() => Moon) }
    }, [])

    const bmi = calculateBMI(profile?.weight, profile?.height)
    const bmiCategory = getBMICategory(bmi)
    const calorieGoal = profile?.calorie_goal || calculateCalorieGoal(profile)
    const hasProfile = profile?.weight && profile?.height && profile?.age
    const goal = goalConfig[profile?.goal] || goalConfig.maintain
    const userDiet = profile?.diet?.toLowerCase()?.replace(/\s+/g, '-') || null
    const diet = dietConfig[userDiet] || defaultDiet
    const macroGoals = getMacroGoals(profile)
    const dietInfo = getDietInfo(profile?.diet)

    if (isLoading) {
        return (
            <div className="min-h-full pb-8 animate-pulse">
                <div className="h-16 w-64 rounded-xl mb-6" style={{ background: 'var(--color-bg-tertiary)' }} />
                <div className="grid grid-cols-2 gap-3 mb-6">
                    {[1, 2, 3, 4].map(i => <div key={i} className="h-28 rounded-2xl" style={{ background: 'var(--color-bg-tertiary)' }} />)}
                </div>
                <div className="h-52 rounded-2xl mb-6" style={{ background: 'var(--color-bg-tertiary)' }} />
                <div className="h-32 rounded-2xl" style={{ background: 'var(--color-bg-tertiary)' }} />
            </div>
        )
    }

    return (
        <div className="min-h-full pb-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <div className="flex items-center gap-2 mb-0.5">
                        <TimeIcon className="w-4 h-4" style={{ color: '#10B981' }} />
                        <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>{greeting}</span>
                    </div>
                    <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                        {profile?.name ? profile.name.split(' ')[0] : 'Welcome'}
                    </h1>
                </div>
                <Link to="/profile" className="w-11 h-11 rounded-xl flex items-center justify-center transition-all hover:scale-105 hover:shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)' }}>
                    <User className="w-5 h-5" style={{ color: '#FFFFFF' }} />
                </Link>
            </div>

            {/* Complete profile CTA */}
            {!hasProfile && (
                <Link to="/profile" className="flex items-center gap-4 p-4 mb-6 rounded-2xl transition-all hover:scale-[1.01] hover:shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #F59E0B15 0%, #F59E0B05 100%)', border: '1px solid #F59E0B25' }}>
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)' }}>
                        <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1">
                        <p className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>Complete your profile</p>
                        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Get personalized nutrition insights</p>
                    </div>
                    <ChevronRight className="w-5 h-5" style={{ color: '#F59E0B' }} />
                </Link>
            )}

            {hasProfile && (
                <>
                    {/* Stats grid - 3 columns on larger screens */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3 mb-5">
                        <StatCard icon={Scale} value={bmi} label="BMI" sublabel={bmiCategory.label} color={bmiCategory.color} />
                        <StatCard icon={Activity} value={`${profile?.weight || '--'} kg`} label="Weight" color="#3B82F6" gradient="linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)" />
                        <StatCard icon={Ruler} value={`${profile?.height || '--'} cm`} label="Height" color="#8B5CF6" gradient="linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)" />
                        <StatCard icon={goal.Icon} value={goal.label} label="Goal" color={goal.color} gradient={goal.gradient} />
                        {userDiet ? (
                            <StatCard icon={diet.Icon || Utensils} value={diet.label} label="Diet" color={diet.color} />
                        ) : (
                            <StatCard icon={User} value={`${profile?.age || '--'} yrs`} label="Age" color="#EC4899" gradient="linear-gradient(135deg, #EC4899 0%, #DB2777 100%)" />
                        )}
                        {userDiet && <StatCard icon={User} value={`${profile?.age || '--'} yrs`} label="Age" color="#EC4899" gradient="linear-gradient(135deg, #EC4899 0%, #DB2777 100%)" />}
                    </div>

                    {/* Diet tip */}
                    {userDiet && (
                        <div className="flex items-center gap-3 p-4 mb-5 rounded-xl"
                            style={{ background: `linear-gradient(135deg, ${diet.color}12 0%, ${diet.color}05 100%)`, border: `1px solid ${diet.color}20` }}>
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: diet.color + '20' }}>
                                <Lightbulb className="w-4 h-4" style={{ color: diet.color }} />
                            </div>
                            <div className="flex-1">
                                <p className="text-xs font-semibold mb-0.5" style={{ color: diet.color }}>Pro Tip</p>
                                <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{diet.tip}</p>
                            </div>
                        </div>
                    )}

                    {/* Daily Nutrition Target */}
                    {calorieGoal && (
                        <div className="rounded-xl sm:rounded-2xl p-4 sm:p-5 mb-5 overflow-hidden relative"
                            style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
                            {/* Background decoration */}
                            <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-5"
                                style={{ background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)', transform: 'translate(30%, -30%)' }} />

                            <div className="flex items-center gap-3 sm:gap-4 mb-4 sm:mb-5">
                                <div className="w-11 h-11 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl flex items-center justify-center"
                                    style={{ background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)', boxShadow: '0 8px 24px rgba(249, 115, 22, 0.35)' }}>
                                    <Flame className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
                                </div>
                                <div className="flex-1">
                                    <p className="text-[10px] sm:text-xs font-semibold uppercase tracking-wider mb-0.5" style={{ color: 'var(--color-text-muted)' }}>
                                        Daily Nutrition Target
                                    </p>
                                    <div className="flex items-baseline gap-2">
                                        <p className="text-2xl sm:text-3xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                            {calorieGoal.toLocaleString()}
                                        </p>
                                        <span className="text-xs sm:text-sm font-medium" style={{ color: 'var(--color-text-muted)' }}>kcal</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-[10px] font-medium uppercase" style={{ color: 'var(--color-text-muted)' }}>Macro Split</p>
                                    <p className="text-[10px] sm:text-xs font-bold" style={{ color: '#10B981' }}>
                                        {dietInfo.protein}P / {dietInfo.carbs}C / {dietInfo.fat}F
                                    </p>
                                </div>
                            </div>

                            {/* Macro rings */}
                            <div className="flex justify-around pt-4" style={{ borderTop: '1px solid var(--color-border)' }}>
                                <MacroProgress value={macroGoals.protein} max={macroGoals.protein} color="#3B82F6" icon={Drumstick} label="Protein" />
                                <MacroProgress value={macroGoals.carbs} max={macroGoals.carbs} color="#10B981" icon={Wheat} label="Carbs" />
                                <MacroProgress value={macroGoals.fat} max={macroGoals.fat} color="#F59E0B" icon={Droplets} label="Fat" />
                            </div>

                            {/* Source reference */}
                            <p className="text-[10px] text-center mt-4 pt-3" style={{ color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)' }}>
                                Based on: {dietInfo.source || 'Evidence-based dietary guidelines'}
                            </p>
                        </div>
                    )}

                    {/* Weekly Progress */}
                    <div className="mb-5">
                        <WeeklyProgress />
                    </div>
                </>
            )}

            {/* Chat CTA */}
            <Link to="/chat" className="flex items-center gap-3 sm:gap-4 p-4 sm:p-5 rounded-xl sm:rounded-2xl transition-all hover:scale-[1.01] hover:shadow-lg overflow-hidden relative"
                style={{ background: 'linear-gradient(135deg, #10B98118 0%, #10B98108 100%)', border: '1px solid #10B98125' }}>
                <div className="absolute top-0 right-0 w-40 h-40 rounded-full opacity-10"
                    style={{ background: '#10B981', transform: 'translate(40%, -40%)' }} />
                <div className="w-11 h-11 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl flex items-center justify-center relative z-10"
                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 8px 24px rgba(16, 185, 129, 0.35)' }}>
                    <Brain className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
                </div>
                <div className="flex-1 relative z-10">
                    <p className="font-bold text-base sm:text-lg" style={{ color: 'var(--color-text-primary)' }}>Chat with NourishGraph AI</p>
                    <p className="text-xs sm:text-sm" style={{ color: 'var(--color-text-muted)' }}>Get personalized nutrition advice & meal plans</p>
                </div>
                <ArrowRight className="w-5 h-5 sm:w-6 sm:h-6 relative z-10" style={{ color: '#10B981' }} />
            </Link>
        </div>
    )
}
