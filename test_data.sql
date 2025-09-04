CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(150),
    age INT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    country VARCHAR(50)
);

INSERT INTO users (name, email, age, created_at, is_active, country)
SELECT
    'User_' || g AS name,
    'user' || g || '@example.com' AS email,
    (30 + (g % 50)) AS age,  -- возраст от 30 до 79
    NOW() - INTERVAL '1 year' * (g % 10) AS created_at,  -- дата от года назад
    CASE WHEN g % 5 = 0 THEN FALSE ELSE TRUE END AS is_active,  -- 20% неактивных
    CASE (g % 10)
        WHEN 0 THEN 'Russia'
        WHEN 1 THEN 'USA'
        WHEN 2 THEN 'Germany'
        WHEN 3 THEN 'France'
        WHEN 4 THEN 'Japan'
        WHEN 5 THEN 'Canada'
        WHEN 6 THEN 'Australia'
        WHEN 7 THEN 'Brazil'
        WHEN 8 THEN 'India'
        WHEN 9 THEN 'South Africa'
    END AS country
FROM generate_series(1, 10000000) AS g;