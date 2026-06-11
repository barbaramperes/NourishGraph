-- Migrates the `users` table columns from Portuguese -> English.
--
-- Run:
--   PGPASSWORD=nutriai_password psql -h localhost -U nutriai_user -d nutriai -f scripts/migrate_users_columns_to_english.sql
DO $$
BEGIN
	-- Only rename if the Portuguese column exists (idempotent).
	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='nome') THEN
		ALTER TABLE users RENAME COLUMN nome TO name;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='idade') THEN
		ALTER TABLE users RENAME COLUMN idade TO age;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='peso') THEN
		ALTER TABLE users RENAME COLUMN peso TO weight;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='altura') THEN
		ALTER TABLE users RENAME COLUMN altura TO height;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='sexo') THEN
		ALTER TABLE users RENAME COLUMN sexo TO gender;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='objetivo') THEN
		ALTER TABLE users RENAME COLUMN objetivo TO goal;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='atividade') THEN
		ALTER TABLE users RENAME COLUMN atividade TO activity;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='restricoes') THEN
		ALTER TABLE users RENAME COLUMN restricoes TO restrictions;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='preferencias') THEN
		ALTER TABLE users RENAME COLUMN preferencias TO preferences;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='imc') THEN
		ALTER TABLE users RENAME COLUMN imc TO bmi;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='tmb') THEN
		ALTER TABLE users RENAME COLUMN tmb TO bmr;
	END IF;

	IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='users' AND column_name='meta_calorica') THEN
		ALTER TABLE users RENAME COLUMN meta_calorica TO calorie_goal;
	END IF;
END
$$;

-- Update functions/triggers to work with English column names and English activity/goal values.

CREATE OR REPLACE FUNCTION public.calc_tdee(tmb integer, atividade character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
	multiplicador DECIMAL;
BEGIN
	IF tmb IS NULL THEN RETURN NULL; END IF;
	multiplicador := CASE atividade
		WHEN 'sedentario' THEN 1.2
		WHEN 'sedentary' THEN 1.2
		WHEN 'leve' THEN 1.375
		WHEN 'light' THEN 1.375
		WHEN 'moderado' THEN 1.55
		WHEN 'moderate' THEN 1.55
		WHEN 'ativo' THEN 1.725
		WHEN 'active' THEN 1.725
		WHEN 'muito_ativo' THEN 1.9
		WHEN 'very_active' THEN 1.9
		ELSE 1.2
	END;
	RETURN ROUND(tmb * multiplicador);
END;
$function$;

CREATE OR REPLACE FUNCTION public.update_user_metrics()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
	new_bmi DECIMAL;
	new_bmr INTEGER;
	new_tdee INTEGER;
	new_calorie_goal INTEGER;
BEGIN
	new_bmi := calc_imc(NEW.weight, NEW.height);
	new_bmr := calc_tmb(NEW.weight, NEW.height, NEW.age, NEW.gender);
	new_tdee := calc_tdee(new_bmr, NEW.activity);

	IF new_tdee IS NOT NULL THEN
		new_calorie_goal := CASE
			WHEN NEW.goal ILIKE '%perder%' OR NEW.goal ILIKE '%lose%' OR NEW.goal = 'lose' THEN new_tdee - 500
			WHEN NEW.goal ILIKE '%ganhar%' OR NEW.goal ILIKE '%gain%' OR NEW.goal = 'gain' THEN new_tdee + 300
			ELSE new_tdee
		END;
	END IF;

	NEW.bmi := new_bmi;
	NEW.bmr := new_bmr;
	NEW.tdee := new_tdee;
	NEW.calorie_goal := new_calorie_goal;

	RETURN NEW;
END;
$function$;

-- Normalize defaults/data to English (keeps backward compatibility in calc_tdee/update_user_metrics).

ALTER TABLE public.users
ALTER COLUMN activity
SET DEFAULT 'sedentary';

UPDATE public.users
SET
    activity = CASE activity
        WHEN 'sedentario' THEN 'sedentary'
        WHEN 'leve' THEN 'light'
        WHEN 'moderado' THEN 'moderate'
        WHEN 'ativo' THEN 'active'
        WHEN 'muito_ativo' THEN 'very_active'
        ELSE activity
    END
WHERE
    activity IN (
        'sedentario',
        'leve',
        'moderado',
        'ativo',
        'muito_ativo'
    );

UPDATE public.users
SET
    goal = CASE
        WHEN goal ILIKE '%perder%' THEN 'lose'
        WHEN goal ILIKE '%ganhar%' THEN 'gain'
        ELSE goal
    END
WHERE
    goal IS NOT NULL;