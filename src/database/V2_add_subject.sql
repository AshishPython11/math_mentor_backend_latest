INSERT INTO subjects (name)
VALUES 
    ('Maths'),
    ('Physics'),
    ('Biology'),
    ('Chemistry'),
    ('General')
ON CONFLICT (name) DO NOTHING;
