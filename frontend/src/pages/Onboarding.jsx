import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import { Target, Flame, Dumbbell, Scale, Utensils, AlertTriangle } from 'lucide-react'

const allergyOptions = [
    { id: 'nuts', label: 'Tree Nuts', desc: 'Almonds, walnuts, cashews, etc.' },
    { id: 'peanuts', label: 'Peanuts', desc: 'Peanuts and peanut products' },
    { id: 'dairy', label: 'Dairy/Lactose', desc: 'Milk, cheese, butter, etc.' },
    { id: 'eggs', label: 'Eggs', desc: 'Eggs and egg products' },
    { id: 'shellfish', label: 'Shellfish', desc: 'Shrimp, crab, lobster, etc.' },
    { id: 'fish', label: 'Fish', desc: 'All types of fish' },
    { id: 'soy', label: 'Soy', desc: 'Soybeans and soy products' },
    { id: 'wheat', label: 'Wheat/Gluten', desc: 'Wheat, barley, rye' },
    { id: 'sesame', label: 'Sesame', desc: 'Sesame seeds and oil' },
]

const dietTypes = [
    { id: '', label: 'No specific diet', desc: 'No dietary restrictions' },
    { id: 'mediterranean', label: 'Mediterranean', desc: 'Olive oil, fish, whole grains' },
    { id: 'vegetarian', label: 'Vegetarian', desc: 'No meat, includes dairy/eggs' },
    { id: 'vegan', label: 'Vegan', desc: 'No animal products' },
    { id: 'keto', label: 'Ketogenic (Keto)', desc: 'High fat, very low carb' },
    { id: 'carnivore', label: 'Carnivore', desc: 'Meat-based, no plants' },
    { id: 'animal-based', label: 'Animal-Based', desc: 'Prioritizes animal foods, allows some fruit/honey' },
    { id: 'paleo', label: 'Paleo', desc: 'Whole foods, no grains/dairy' },
    { id: 'ancestral', label: 'Ancestral', desc: 'Traditional whole foods' },
    { id: 'gluten-free', label: 'Gluten-Free', desc: 'No wheat, barley, rye' },
    { id: 'low-carb', label: 'Low-Carb', desc: 'Reduced carbohydrates' },
    { id: 'other', label: 'Other', desc: 'Specify your own diet' },
]

const goals = [
    { id: 'lose_weight', label: 'Lose Weight', icon: Flame, gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', desc: 'Burn fat & slim down' },
    { id: 'maintain', label: 'Maintain', icon: Scale, gradient: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)', desc: 'Keep your current weight' },
    { id: 'gain_muscle', label: 'Gain Muscle', icon: Dumbbell, gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', desc: 'Build strength & mass' },
]

const activityLevels = [
    { id: 'sedentary', label: 'Sedentary', desc: 'Office work, little exercise' },
    { id: 'light', label: 'Lightly Active', desc: '1-3 days/week' },
    { id: 'moderate', label: 'Moderately Active', desc: '3-5 days/week' },
    { id: 'active', label: 'Very Active', desc: '6-7 days/week' },
    { id: 'very_active', label: 'Extremely Active', desc: 'Athlete level' },
]

export default function Onboarding() {
    const navigate = useNavigate()
    const { user, completeOnboarding } = useAuthStore()
    const { saveProfile } = useAppStore()

    const [step, setStep] = useState(1)
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState({
        age: '',
        sex: '',
        weight: '',
        height: '',
        goal: '',
        activity: '',
        diet: '',
        customDiet: '',
        allergies: []
    })

    const updateData = (key, value) => {
        setData(prev => ({ ...prev, [key]: value }))
    }

    const handleComplete = async () => {
        // Validate data before saving
        const age = parseInt(data.age)
        const weight = parseFloat(data.weight)
        const height = parseFloat(data.height)

        // Ensure values are within valid ranges
        const validAge = !isNaN(age) && age >= 13 && age <= 120 ? age : null
        const validWeight = !isNaN(weight) && weight >= 30 && weight <= 300 ? weight : null
        const validHeight = !isNaN(height) && height >= 100 && height <= 250 ? height : null

        if (!validAge || !validWeight || !validHeight) {
            return // Don't proceed if validation fails
        }

        setLoading(true)

        try {
            const profileData = {
                name: user?.name || '',
                email: user?.email || '',
                age: validAge,
                gender: data.sex,
                weight: validWeight,
                height: validHeight,
                goal: data.goal,
                activity: data.activity,
                diet: data.diet === 'other' ? (data.customDiet || 'other') : (data.diet || null),
                restrictions: [],
                allergies: data.allergies || []
            }
            console.log('[Onboarding] Saving profile with diet:', profileData.diet)
            
            const result = await saveProfile(profileData)
            console.log('[Onboarding] Save result, diet:', result?.diet)

            completeOnboarding()
            navigate('/')
        } catch (err) {
            console.error('[Onboarding] Save error:', err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 sm:p-6"
            style={{ background: 'var(--color-bg-primary)' }}>
            {/* Background effects */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-[250px] sm:w-[400px] md:w-[500px] h-[250px] sm:h-[400px] md:h-[500px] rounded-full blur-[80px] sm:blur-[120px] opacity-20"
                    style={{ background: 'radial-gradient(circle, #10B981 0%, transparent 70%)' }} />
                <div className="absolute bottom-1/4 right-1/4 w-[200px] sm:w-[300px] md:w-[400px] h-[200px] sm:h-[300px] md:h-[400px] rounded-full blur-[60px] sm:blur-[100px] opacity-15"
                    style={{ background: 'radial-gradient(circle, #14B8A6 0%, transparent 70%)' }} />
            </div>

            <div className="w-full max-w-lg animate-slideUp relative z-10">
                {/* Progress */}
                <div className="flex gap-1.5 sm:gap-2 mb-6 sm:mb-8">
                    {[1, 2, 3, 4, 5].map((s) => (
                        <div
                            key={s}
                            className="h-1 sm:h-1.5 flex-1 rounded-full transition-all duration-500"
                            style={{
                                background: s <= step
                                    ? 'linear-gradient(90deg, #059669 0%, #10B981 100%)'
                                    : 'rgba(255, 255, 255, 0.1)',
                                boxShadow: s <= step ? '0 0 10px rgba(16, 185, 129, 0.5)' : 'none'
                            }}
                        />
                    ))}
                </div>

                {/* Step 1: Basic Info */}
                {step === 1 && (
                    <div className="space-y-4 sm:space-y-6">
                        <div className="text-center mb-6 sm:mb-8">
                            <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-xl sm:rounded-2xl flex items-center justify-center mx-auto mb-3 sm:mb-4"
                                style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(20, 184, 166, 0.2) 100%)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                                <Target className="w-7 h-7 sm:w-10 sm:h-10" style={{ color: '#10B981' }} />
                            </div>
                            <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold mb-1.5 sm:mb-2"
                                style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Let's personalize your experience
                            </h1>
                            <p className="text-xs sm:text-sm md:text-base" style={{ color: 'var(--color-text-muted)' }}>Tell us about yourself for accurate recommendations</p>
                        </div>

                        <div className="grid grid-cols-2 gap-3 sm:gap-4">
                            <div className="space-y-1.5 sm:space-y-2">
                                <label className="text-xs sm:text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>Age</label>
                                <input
                                    type="number"
                                    value={data.age}
                                    onChange={(e) => updateData('age', e.target.value)}
                                    placeholder="30"
                                    min={13}
                                    max={120}
                                    className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base transition-all focus:outline-none"
                                    style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                                />
                            </div>

                            <div className="space-y-1.5 sm:space-y-2">
                                <label className="text-xs sm:text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>Sex</label>
                                <select
                                    value={data.sex}
                                    onChange={(e) => updateData('sex', e.target.value)}
                                    className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base transition-all focus:outline-none"
                                    style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                                >
                                    <option value="">Select...</option>
                                    <option value="M">Male</option>
                                    <option value="F">Female</option>
                                </select>
                            </div>

                            <div className="space-y-1.5 sm:space-y-2">
                                <label className="text-xs sm:text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>Weight (kg)</label>
                                <input
                                    type="number"
                                    value={data.weight}
                                    onChange={(e) => updateData('weight', e.target.value)}
                                    placeholder="70"
                                    step={0.1}
                                    min={30}
                                    max={300}
                                    className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base transition-all focus:outline-none"
                                    style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                                />
                            </div>

                            <div className="space-y-1.5 sm:space-y-2">
                                <label className="text-xs sm:text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>Height (cm)</label>
                                <input
                                    type="number"
                                    value={data.height}
                                    onChange={(e) => updateData('height', e.target.value)}
                                    placeholder="175"
                                    min={100}
                                    max={250}
                                    className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base transition-all focus:outline-none"
                                    style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                                />
                            </div>
                        </div>

                        <button
                            onClick={() => setStep(2)}
                            disabled={!data.age || !data.sex || !data.weight || !data.height}
                            className="w-full py-3 sm:py-4 text-white text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-1 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                            style={{
                                background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                                boxShadow: (!data.age || !data.sex || !data.weight || !data.height) ? 'none' : '0 10px 40px rgba(16, 185, 129, 0.3)'
                            }}
                        >
                            Continue →
                        </button>
                    </div>
                )}

                {/* Step 2: Goal */}
                {step === 2 && (
                    <div className="space-y-4 sm:space-y-6">
                        <div className="text-center mb-6 sm:mb-8">
                            <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold mb-1.5 sm:mb-2"
                                style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                What's your goal?
                            </h1>
                            <p className="text-xs sm:text-sm md:text-base" style={{ color: 'var(--color-text-muted)' }}>We'll personalize your calorie targets</p>
                        </div>

                        <div className="space-y-2 sm:space-y-3">
                            {goals.map((goal) => (
                                <button
                                    key={goal.id}
                                    onClick={() => updateData('goal', goal.id)}
                                    className="w-full flex items-center gap-3 sm:gap-4 p-3 sm:p-5 rounded-lg sm:rounded-xl transition-all hover:-translate-y-1"
                                    style={{
                                        background: data.goal === goal.id
                                            ? 'rgba(16, 185, 129, 0.1)'
                                            : 'var(--color-input-bg)',
                                        border: data.goal === goal.id
                                            ? '1px solid rgba(16, 185, 129, 0.4)'
                                            : '1px solid var(--color-input-border)',
                                        boxShadow: data.goal === goal.id ? '0 8px 25px rgba(16, 185, 129, 0.15)' : 'none'
                                    }}
                                >
                                    <div className="w-10 h-10 sm:w-14 sm:h-14 rounded-lg sm:rounded-xl flex items-center justify-center shrink-0"
                                        style={{ background: goal.gradient }}>
                                        <goal.icon className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
                                    </div>
                                    <div className="text-left flex-1 min-w-0">
                                        <div className="font-bold text-sm sm:text-lg" style={{ color: 'var(--color-text-primary)' }}>{goal.label}</div>
                                        <div className="text-xs sm:text-sm truncate" style={{ color: 'var(--color-text-muted)' }}>{goal.desc}</div>
                                    </div>
                                    {data.goal === goal.id && (
                                        <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center shrink-0"
                                            style={{ background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)' }}>
                                            <svg className="w-3 h-3 sm:w-4 sm:h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="flex gap-2 sm:gap-3">
                            <button
                                onClick={() => setStep(1)}
                                className="flex-1 py-3 sm:py-4 text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                            >
                                ← Back
                            </button>
                            <button
                                onClick={() => setStep(3)}
                                disabled={!data.goal}
                                className="flex-1 py-3 sm:py-4 text-white text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-1 disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                                style={{
                                    background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                                    boxShadow: !data.goal ? 'none' : '0 10px 40px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                Continue →
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 3: Activity Level */}
                {step === 3 && (
                    <div className="space-y-4 sm:space-y-6">
                        <div className="text-center mb-6 sm:mb-8">
                            <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold mb-1.5 sm:mb-2"
                                style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                How active are you?
                            </h1>
                            <p className="text-xs sm:text-sm md:text-base" style={{ color: 'var(--color-text-muted)' }}>This helps calculate your daily needs</p>
                        </div>

                        <div className="space-y-1.5 sm:space-y-2">
                            {activityLevels.map((level, index) => (
                                <button
                                    key={level.id}
                                    onClick={() => updateData('activity', level.id)}
                                    className="w-full flex items-center justify-between p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                    style={{
                                        background: data.activity === level.id
                                            ? 'rgba(16, 185, 129, 0.1)'
                                            : 'var(--color-input-bg)',
                                        border: data.activity === level.id
                                            ? '1px solid rgba(16, 185, 129, 0.4)'
                                            : '1px solid var(--color-input-border)'
                                    }}
                                >
                                    <div className="flex items-center gap-2 sm:gap-3">
                                        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-md sm:rounded-lg flex items-center justify-center font-bold text-xs sm:text-sm shrink-0"
                                            style={{
                                                background: data.activity === level.id
                                                    ? 'linear-gradient(135deg, #059669 0%, #10B981 100%)'
                                                    : 'rgba(255, 255, 255, 0.05)',
                                                color: data.activity === level.id ? 'white' : 'var(--color-text-muted)'
                                            }}>
                                            {index + 1}
                                        </div>
                                        <div className="text-left min-w-0">
                                            <div className="font-semibold text-sm sm:text-base" style={{ color: data.activity === level.id ? '#10B981' : 'var(--color-text-primary)' }}>{level.label}</div>
                                            <div className="text-xs sm:text-sm truncate" style={{ color: 'var(--color-text-muted)' }}>{level.desc}</div>
                                        </div>
                                    </div>
                                    {data.activity === level.id && (
                                        <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center shrink-0"
                                            style={{ background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)' }}>
                                            <svg className="w-3 h-3 sm:w-4 sm:h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="flex gap-2 sm:gap-3">
                            <button
                                onClick={() => setStep(2)}
                                className="flex-1 py-3 sm:py-4 text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                            >
                                ← Back
                            </button>
                            <button
                                onClick={() => setStep(4)}
                                disabled={!data.activity}
                                className="flex-1 py-3 sm:py-4 text-white text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-1 disabled:opacity-60"
                                style={{
                                    background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                                    boxShadow: !data.activity ? 'none' : '0 10px 40px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                Continue →
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 4: Diet Type */}
                {step === 4 && (
                    <div className="space-y-4 sm:space-y-6">
                        <div className="text-center mb-6 sm:mb-8">
                            <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-xl sm:rounded-2xl flex items-center justify-center mx-auto mb-3 sm:mb-4"
                                style={{ background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(16, 185, 129, 0.2) 100%)', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
                                <Utensils className="w-7 h-7 sm:w-10 sm:h-10" style={{ color: '#22C55E' }} />
                            </div>
                            <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold mb-1.5 sm:mb-2"
                                style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Any dietary preferences?
                            </h1>
                            <p className="text-xs sm:text-sm md:text-base" style={{ color: 'var(--color-text-muted)' }}>Optional - helps personalize meal suggestions</p>
                        </div>

                        <div className="space-y-1.5 sm:space-y-2">
                            {dietTypes.map((diet) => (
                                <button
                                    key={diet.id}
                                    onClick={() => updateData('diet', diet.id)}
                                    className="w-full flex items-center justify-between p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                    style={{
                                        background: data.diet === diet.id
                                            ? 'rgba(34, 197, 94, 0.1)'
                                            : 'var(--color-input-bg)',
                                        border: data.diet === diet.id
                                            ? '1px solid rgba(34, 197, 94, 0.4)'
                                            : '1px solid var(--color-input-border)'
                                    }}
                                >
                                    <div className="text-left min-w-0">
                                        <div className="font-semibold text-sm sm:text-base" style={{ color: data.diet === diet.id ? '#22C55E' : 'var(--color-text-primary)' }}>{diet.label}</div>
                                        <div className="text-xs sm:text-sm truncate" style={{ color: 'var(--color-text-muted)' }}>{diet.desc}</div>
                                    </div>
                                    {data.diet === diet.id && (
                                        <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center shrink-0"
                                            style={{ background: 'linear-gradient(135deg, #16A34A 0%, #22C55E 100%)' }}>
                                            <svg className="w-3 h-3 sm:w-4 sm:h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                <polyline points="20 6 9 17 4 12"></polyline>
                                            </svg>
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* Custom diet text input when "Other" is selected */}
                        {data.diet === 'other' && (
                            <div className="space-y-1.5 sm:space-y-2">
                                <label className="text-xs sm:text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
                                    Specify your diet
                                </label>
                                <input
                                    type="text"
                                    value={data.customDiet}
                                    onChange={(e) => updateData('customDiet', e.target.value)}
                                    placeholder="e.g. Pescatarian, Whole30, FODMAP..."
                                    maxLength={50}
                                    className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base transition-all focus:outline-none"
                                    style={{ 
                                        background: 'var(--color-input-bg)', 
                                        border: '1px solid rgba(34, 197, 94, 0.4)', 
                                        color: 'var(--color-text-primary)' 
                                    }}
                                />
                            </div>
                        )}

                        <div className="flex gap-2 sm:gap-3">
                            <button
                                onClick={() => setStep(3)}
                                className="flex-1 py-3 sm:py-4 text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                            >
                                ← Back
                            </button>
                            <button
                                onClick={() => setStep(5)}
                                className="flex-1 py-3 sm:py-4 text-white text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-1"
                                style={{
                                    background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                                    boxShadow: '0 10px 40px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                Continue →
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 5: Food Allergies */}
                {step === 5 && (
                    <div className="space-y-4 sm:space-y-6">
                        <div className="text-center mb-6 sm:mb-8">
                            <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-xl sm:rounded-2xl flex items-center justify-center mx-auto mb-3 sm:mb-4"
                                style={{ background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                                <AlertTriangle className="w-7 h-7 sm:w-10 sm:h-10" style={{ color: '#EF4444' }} />
                            </div>
                            <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-bold mb-1.5 sm:mb-2"
                                style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Any food allergies?
                            </h1>
                            <p className="text-xs sm:text-sm md:text-base" style={{ color: 'var(--color-text-muted)' }}>Optional — select all that apply, we'll exclude these from meal suggestions</p>
                            <p className="text-[10px] sm:text-xs mt-1" style={{ color: 'var(--color-text-muted)', opacity: 0.7 }}>You can skip this step if you have no allergies</p>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                            {allergyOptions.map((allergy) => {
                                const isSelected = data.allergies.includes(allergy.id);
                                return (
                                    <button
                                        key={allergy.id}
                                        onClick={() => {
                                            const newAllergies = isSelected
                                                ? data.allergies.filter(a => a !== allergy.id)
                                                : [...data.allergies, allergy.id];
                                            updateData('allergies', newAllergies);
                                        }}
                                        className="flex flex-col items-center p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                        style={{
                                            background: isSelected
                                                ? 'rgba(239, 68, 68, 0.15)'
                                                : 'var(--color-input-bg)',
                                            border: isSelected
                                                ? '1px solid rgba(239, 68, 68, 0.5)'
                                                : '1px solid var(--color-input-border)'
                                        }}
                                    >
                                        <div className="font-semibold text-xs sm:text-sm mb-0.5" style={{ color: isSelected ? '#EF4444' : 'var(--color-text-primary)' }}>
                                            {allergy.label}
                                        </div>
                                        <div className="text-[10px] sm:text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                                            {allergy.desc}
                                        </div>
                                        {isSelected && (
                                            <div className="w-4 h-4 sm:w-5 sm:h-5 rounded-full flex items-center justify-center mt-1.5"
                                                style={{ background: 'linear-gradient(135deg, #DC2626 0%, #EF4444 100%)' }}>
                                                <svg className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                    <polyline points="20 6 9 17 4 12"></polyline>
                                                </svg>
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>

                        {data.allergies.length > 0 && (
                            <div className="p-3 sm:p-4 rounded-lg sm:rounded-xl" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                                <div className="text-xs sm:text-sm" style={{ color: '#EF4444' }}>
                                    <strong>Selected:</strong> {data.allergies.map(id => allergyOptions.find(a => a.id === id)?.label).join(', ')}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2 sm:gap-3">
                            <button
                                onClick={() => setStep(4)}
                                className="flex-1 py-3 sm:py-4 text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-0.5"
                                style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                            >
                                ← Back
                            </button>
                            <button
                                onClick={handleComplete}
                                disabled={loading}
                                className="flex-1 py-3 sm:py-4 text-white text-sm sm:text-base font-bold rounded-lg sm:rounded-xl transition-all hover:-translate-y-1 disabled:opacity-60"
                                style={{
                                    background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
                                    boxShadow: '0 10px 40px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <svg className="animate-spin w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                        Saving...
                                    </span>
                                ) : 'Start My Journey →'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
