
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    grade SMALLINT,
    is_paid BOOLEAN DEFAULT FALSE,  
    is_deleted BOOLEAN DEFAULT FALSE, 
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    birth_date DATE
);

CREATE TABLE user_otps(
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE user_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_tokens INT NOT NULL DEFAULT 0, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE user_queries (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer JSONB NOT NULL,
    tokens_used INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE plans (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,  -- e.g., "Basic", "Premium"
    amount DECIMAL(10, 2) NOT NULL,  -- Price of the plan (e.g., $10, $18, $50)
    tokens INT NOT NULL,  -- Number of tokens granted for the plan (e.g., 100, 200, 500)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id BIGINT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    tokens_purchased INT NOT NULL,
    payment_status VARCHAR(20) NOT NULL CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    payer_email VARCHAR(255),
    payment_method VARCHAR(50),
    paypal_order_id VARCHAR(255) UNIQUE NOT NULL,  -- PayPal order ID
    paypal_capture_id VARCHAR(255),  -- PayPal capture ID
    paypal_transaction_id VARCHAR(255), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




CREATE TABLE subjects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id BIGINT REFERENCES subjects(id) ON DELETE SET NULL, -- Allow linking to subjects
    title VARCHAR(255),  -- Optional: Store conversation titles
    is_active BOOLEAN DEFAULT TRUE, -- Helps in marking completed or ongoing chats
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    subject_id BIGINT REFERENCES subjects(id) ON DELETE SET NULL,
    prompt TEXT NOT NULL,
    ai_response JSONB NOT NULL,
    tokens_used INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE, 
    is_active BOOLEAN DEFAULT TRUE
);  




-- MEDIA UPLOADS TABLE: Stores image and audio files uploaded by users
CREATE TABLE media_uploads (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_history_id BIGINT NOT NULL REFERENCES chat_history(id) ON DELETE CASCADE,  -- Fix: Reference chat_history.id instead of conversation_id
    media_type VARCHAR(50) NOT NULL CHECK (media_type IN ('image', 'audio')),
    file_url TEXT NOT NULL,
    processed_text TEXT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


