/**
 * ProfileForm - Professional profile management form
 *
 * Features:
 * - Clean, organized form sections
 * - Real-time validation with helpful messages
 * - Success confirmation animation
 * - Responsive design
 */

import { useState, useEffect } from 'react'
import {
    User,
    Mail,
    Calendar,
    Ruler,
    Weight,
    Target,
    Activity,
    Save,
    Check,
    AlertCircle,
    Utensils,
    AlertTriangle,
    Flame,
    Scale,
    Dumbbell,
    Loader2
} from 'lucide-react'

// Configuration options
export const DIET_TYPES = [
    { id: '', label: 'No specific diet' },
    { id: 'mediterranean', label: 'Mediterranean' },
    { id: 'vegetarian', label: 'Vegetarian' },
    { id: 'vegan', label: 'Vegan' },
    { id: 'keto', label: 'Ketogenic (Keto)' },
    { id: 'carnivore', label: 'Carnivore' },
    { id: 'animal-based', label: 'Animal-Based' },
    { id: 'paleo', label: 'Paleo' },
    { id: 'ancestral', label: 'Ancestral' },
    { id: 'pescatarian', label: 'Pescatarian' },
    { id: 'gluten-free', label: 'Gluten-Free' },
    { id: 'dairy-free', label: 'Dairy-Free' },
    { id: 'low-carb', label: 'Low-Carb' },
    { id: 'other', label: 'Other' },
]

export const GOALS = [
    { id: 'lose_weight', label: 'Lose Weight', icon: Flame, color: '#DC2626' },
    { id: 'maintain', label: 'Maintain', icon: Scale, color: '#059669' },
    { id: 'gain_muscle', label: 'Build Muscle', icon: Dumbbell, color: '#2563EB' },
]

export const ACTIVITY_LEVELS = [
    { id: 'sedentary', label: 'Sedentary', desc: 'Little or no exercise' },
    { id: 'light', label: 'Lightly Active', desc: 'Light exercise 1-3 days/week' },
    { id: 'moderate', label: 'Moderately Active', desc: 'Moderate exercise 3-5 days/week' },
    { id: 'active', label: 'Very Active', desc: 'Hard exercise 6-7 days/week' },
    { id: 'very_active', label: 'Extremely Active', desc: 'Very hard exercise, physical job' },
]

export const ALLERGY_OPTIONS = [
    { id: 'nuts', label: 'Tree Nuts' },
    { id: 'peanuts', label: 'Peanuts' },
    { id: 'dairy', label: 'Dairy/Lactose' },
    { id: 'eggs', label: 'Eggs' },
    { id: 'shellfish', label: 'Shellfish' },
    { id: 'fish', label: 'Fish' },
    { id: 'soy', label: 'Soy' },
    { id: 'wheat', label: 'Wheat/Gluten' },
    { id: 'sesame', label: 'Sesame' },
]

/**
 * Validation rules
 */
const validateField = (field, value) => {
    switch (field) {
        case 'name':
            if (!value?.trim()) return 'Name is required'
            if (value.length < 2) return 'Name must be at least 2 characters'
            return null
        case 'email':
            if (!value?.trim()) return 'Email is required'
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Please enter a valid email'
            return null
        case 'age':
            if (!value) return null // Optional
            const age = parseInt(value)
            if (isNaN(age) || age < 13) return 'Age must be at least 13'
            if (age > 120) return 'Please enter a valid age'
            return null
        case 'weight':
            if (!value) return null // Optional
            const weight = parseFloat(value)
            if (isNaN(weight) || weight < 20) return 'Weight must be at least 20 kg'
            if (weight > 500) return 'Please enter a valid weight'
            return null
        case 'height':
            if (!value) return null // Optional
            const height = parseFloat(value)
            if (isNaN(height) || height < 50) return 'Height must be at least 50 cm'
            if (height > 300) return 'Please enter a valid height'
            return null
        default:
            return null
    }
}

/**
 * Input field with validation
 */
const FormField = ({
    label,
    icon: Icon,
    type = 'text',
    value,
    onChange,
    error,
    placeholder,
    min,
    max,
    step,
    iconColor = 'var(--color-text-muted)'
}) => (
    <div className="space-y-1.5">
        <label className="text-xs sm:text-sm flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
            {Icon && <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" style={{ color: iconColor }} />}
            {label}
        </label>
        <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            min={min}
            max={max}
            step={step}
            className={`w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl text-sm sm:text-base transition-all focus:outline-none focus:ring-2 ${error ? 'focus:ring-red-400/50' : 'focus:ring-emerald-400/50'
                }`}
            style={{
                background: 'var(--color-input-bg)',
                border: error ? '1px solid #EF4444' : '1px solid var(--color-input-border)',
                color: 'var(--color-input-text)'
            }}
        />
        {error && (
            <p className="text-xs flex items-center gap-1 mt-1" style={{ color: '#EF4444' }}>
                <AlertCircle className="w-3 h-3" />
                {error}
            </p>
        )}
    </div>
)

/**
 * Select field
 */
const SelectField = ({
    label,
    icon: Icon,
    value,
    onChange,
    options,
    iconColor = 'var(--color-text-muted)'
}) => (
    <div className="space-y-1.5">
        <label className="text-xs sm:text-sm flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
            {Icon && <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" style={{ color: iconColor }} />}
            {label}
        </label>
        <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl text-sm sm:text-base transition-all focus:outline-none focus:ring-2 focus:ring-emerald-400/50 cursor-pointer"
            style={{
                background: 'var(--color-input-bg)',
                border: '1px solid var(--color-input-border)',
                color: 'var(--color-input-text)',
                appearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%2371717A' viewBox='0 0 16 16'%3E%3Cpath d='M4.5 5.5l3.5 4 3.5-4'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 12px center'
            }}
        >
            {options.map((opt) => (
                <option key={opt.id} value={opt.id}>
                    {opt.label}
                </option>
            ))}
        </select>
    </div>
)

/**
 * Section header
 */
const SectionHeader = ({ icon: Icon, title, color = '#10B981' }) => (
    <h3 className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2" style={{ color }}>
        {Icon && <Icon className="w-4 h-4" />}
        {title}
    </h3>
)

/**
 * Main ProfileForm component
 */
export const ProfileForm = ({
    initialData = {},
    onSave,
    onCancel,
    loading = false,
    compact = false,
    showHeader = true,
    className = ''
}) => {
    const [form, setForm] = useState({
        name: '',
        email: '',
        age: '',
        gender: '',
        weight: '',
        height: '',
        goal: '',
        activity: 'moderate',
        diet: '',
        allergies: [],
        ...initialData
    })

    const [errors, setErrors] = useState({})
    const [touched, setTouched] = useState({})
    const [saveStatus, setSaveStatus] = useState(null) // null | 'saving' | 'success' | 'error'

    // Sync with initialData changes
    useEffect(() => {
        if (initialData && Object.keys(initialData).length > 0) {
            setForm(prev => ({ ...prev, ...initialData }))
        }
    }, [initialData])

    const updateField = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }))
        setTouched(prev => ({ ...prev, [field]: true }))

        // Validate on change
        const error = validateField(field, value)
        setErrors(prev => ({ ...prev, [field]: error }))

        // Reset save status on change
        if (saveStatus === 'success') setSaveStatus(null)
    }

    const toggleAllergy = (allergyId) => {
        setForm(prev => ({
            ...prev,
            allergies: prev.allergies.includes(allergyId)
                ? prev.allergies.filter(a => a !== allergyId)
                : [...prev.allergies, allergyId]
        }))
    }

    const validateAll = () => {
        const newErrors = {}
        let isValid = true

            // Validate required fields
            ;['name', 'email'].forEach(field => {
                const error = validateField(field, form[field])
                if (error) {
                    newErrors[field] = error
                    isValid = false
                }
            })

            // Validate optional numeric fields if provided
            ;['age', 'weight', 'height'].forEach(field => {
                if (form[field]) {
                    const error = validateField(field, form[field])
                    if (error) {
                        newErrors[field] = error
                        isValid = false
                    }
                }
            })

        setErrors(newErrors)
        setTouched({ name: true, email: true, age: true, weight: true, height: true })
        return isValid
    }

    const handleSubmit = async (e) => {
        e?.preventDefault()

        if (!validateAll()) return

        setSaveStatus('saving')

        try {
            await onSave?.({
                ...form,
                age: form.age ? parseInt(form.age) : null,
                weight: form.weight ? parseFloat(form.weight) : null,
                height: form.height ? parseFloat(form.height) : null,
            })
            setSaveStatus('success')

            // Reset success status after animation
            setTimeout(() => setSaveStatus(null), 2000)
        } catch (err) {
            setSaveStatus('error')
            setErrors(prev => ({ ...prev, submit: err.message || 'Failed to save profile' }))
        }
    }

    const hasErrors = Object.values(errors).some(e => e)

    return (
        <form onSubmit={handleSubmit} className={`space-y-6 ${className}`}>
            {/* Personal Information */}
            <div>
                <SectionHeader icon={User} title="Personal Information" color="#10B981" />
                <div className={`grid ${compact ? 'grid-cols-1' : 'sm:grid-cols-2'} gap-4`}>
                    <FormField
                        label="Full Name"
                        icon={User}
                        value={form.name}
                        onChange={(v) => updateField('name', v)}
                        error={touched.name && errors.name}
                        placeholder="Your name"
                        iconColor="#10B981"
                    />
                    <FormField
                        label="Email"
                        icon={Mail}
                        type="email"
                        value={form.email}
                        onChange={(v) => updateField('email', v)}
                        error={touched.email && errors.email}
                        placeholder="your@email.com"
                        iconColor="#10B981"
                    />
                    <FormField
                        label="Age"
                        icon={Calendar}
                        type="number"
                        value={form.age}
                        onChange={(v) => updateField('age', v)}
                        error={touched.age && errors.age}
                        placeholder="30"
                        min={13}
                        max={120}
                    />
                    <SelectField
                        label="Sex"
                        value={form.gender}
                        onChange={(v) => updateField('gender', v)}
                        options={[
                            { id: '', label: 'Select...' },
                            { id: 'M', label: 'Male' },
                            { id: 'F', label: 'Female' }
                        ]}
                    />
                </div>
            </div>

            {/* Body Metrics */}
            <div>
                <SectionHeader icon={Scale} title="Body Metrics" color="#3B82F6" />
                <div className={`grid ${compact ? 'grid-cols-1' : 'sm:grid-cols-2'} gap-4`}>
                    <FormField
                        label="Weight (kg)"
                        icon={Weight}
                        type="number"
                        value={form.weight}
                        onChange={(v) => updateField('weight', v)}
                        error={touched.weight && errors.weight}
                        placeholder="70"
                        min={20}
                        max={500}
                        step={0.1}
                        iconColor="#3B82F6"
                    />
                    <FormField
                        label="Height (cm)"
                        icon={Ruler}
                        type="number"
                        value={form.height}
                        onChange={(v) => updateField('height', v)}
                        error={touched.height && errors.height}
                        placeholder="175"
                        min={50}
                        max={300}
                        iconColor="#3B82F6"
                    />
                </div>
            </div>

            {/* Goal Selection */}
            <div>
                <SectionHeader icon={Target} title="Your Goal" color="#A855F7" />
                <div className="grid grid-cols-3 gap-3">
                    {GOALS.map((g) => {
                        const isSelected = form.goal === g.id
                        const Icon = g.icon
                        return (
                            <button
                                key={g.id}
                                type="button"
                                onClick={() => updateField('goal', g.id)}
                                className="p-4 rounded-xl text-center transition-all hover:-translate-y-1"
                                style={{
                                    background: isSelected
                                        ? `linear-gradient(135deg, ${g.color}15 0%, ${g.color}08 100%)`
                                        : 'var(--color-input-bg)',
                                    border: isSelected
                                        ? `2px solid ${g.color}80`
                                        : '1px solid var(--color-input-border)',
                                    boxShadow: isSelected ? `0 8px 25px ${g.color}15` : 'none'
                                }}
                            >
                                <Icon
                                    className="w-6 h-6 mx-auto mb-2"
                                    style={{ color: isSelected ? g.color : 'var(--color-text-muted)' }}
                                />
                                <div
                                    className="text-xs sm:text-sm font-medium"
                                    style={{ color: isSelected ? g.color : 'var(--color-text-secondary)' }}
                                >
                                    {g.label}
                                </div>
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Activity Level */}
            <div>
                <SectionHeader icon={Activity} title="Activity Level" color="#F59E0B" />
                <SelectField
                    label="How active are you?"
                    icon={Activity}
                    value={form.activity}
                    onChange={(v) => updateField('activity', v)}
                    options={ACTIVITY_LEVELS.map(l => ({ id: l.id, label: `${l.label} - ${l.desc}` }))}
                    iconColor="#F59E0B"
                />
            </div>

            {/* Diet Type */}
            <div>
                <SectionHeader icon={Utensils} title="Diet Preferences" color="#22C55E" />
                <SelectField
                    label="Diet Type"
                    icon={Utensils}
                    value={form.diet}
                    onChange={(v) => updateField('diet', v)}
                    options={DIET_TYPES}
                    iconColor="#22C55E"
                />
            </div>

            {/* Allergies */}
            <div>
                <SectionHeader icon={AlertTriangle} title="Food Allergies" color="#EF4444" />
                <p className="text-xs mb-3" style={{ color: 'var(--color-text-muted)' }}>
                    Select any allergies (meals will exclude these ingredients)
                </p>
                <div className="flex flex-wrap gap-2">
                    {ALLERGY_OPTIONS.map((allergy) => {
                        const isSelected = form.allergies.includes(allergy.id)
                        return (
                            <button
                                key={allergy.id}
                                type="button"
                                onClick={() => toggleAllergy(allergy.id)}
                                className="px-3 py-2 rounded-lg text-xs sm:text-sm transition-all"
                                style={{
                                    background: isSelected
                                        ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%)'
                                        : 'var(--color-input-bg)',
                                    border: isSelected
                                        ? '1px solid rgba(239, 68, 68, 0.5)'
                                        : '1px solid var(--color-input-border)',
                                    color: isSelected ? '#EF4444' : 'var(--color-text-secondary)'
                                }}
                            >
                                {isSelected && <Check className="w-3 h-3 inline mr-1" />}
                                {allergy.label}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Submit Error */}
            {errors.submit && (
                <div
                    className="p-3 rounded-xl flex items-center gap-2 text-sm"
                    style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        color: '#EF4444'
                    }}
                >
                    <AlertCircle className="w-4 h-4" />
                    {errors.submit}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
                {onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="flex-1 py-3 rounded-xl text-sm font-medium transition-all hover:-translate-y-0.5"
                        style={{
                            background: 'var(--color-input-bg)',
                            border: '1px solid var(--color-input-border)',
                            color: 'var(--color-text-secondary)'
                        }}
                    >
                        Cancel
                    </button>
                )}
                <button
                    type="submit"
                    disabled={loading || saveStatus === 'saving' || hasErrors}
                    className={`${onCancel ? 'flex-1' : 'w-full'} py-3 rounded-xl text-sm font-bold transition-all hover:-translate-y-0.5 disabled:opacity-60 disabled:transform-none flex items-center justify-center gap-2`}
                    style={{
                        background: saveStatus === 'success'
                            ? 'linear-gradient(135deg, #22C55E 0%, #16A34A 100%)'
                            : 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                        color: 'white',
                        boxShadow: saveStatus === 'success'
                            ? '0 8px 25px rgba(34, 197, 94, 0.3)'
                            : '0 8px 25px rgba(16, 185, 129, 0.3)'
                    }}
                >
                    {saveStatus === 'saving' || loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Saving...
                        </>
                    ) : saveStatus === 'success' ? (
                        <>
                            <Check className="w-4 h-4" />
                            Saved Successfully!
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />
                            Save Profile
                        </>
                    )}
                </button>
            </div>
        </form>
    )
}

export default ProfileForm
