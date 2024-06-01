CREATE TABLE IF NOT EXISTS screentime (
    user_id BIGINT,
    online INTEGER DEFAULT 0,
    idle INTEGER DEFAULT 0,
    dnd INTEGER DEFAULT 0,
    offline INTEGER DEFAULT 0,
    time TIMESTAMP,
    PRIMARY KEY (user_id, time)
);


CREATE TABLE IF NOT EXISTS prefixes (
    guild_id BIGINT PRIMARY KEY,
    prefix TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS emoji_operations (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    emoji_id TEXT,
    emoji_name TEXT,
    operation_type TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS sticker_operations (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    sticker_id TEXT,
    sticker_name TEXT,
    operation_type TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS afk (
    user_id BIGINT PRIMARY KEY,
    reason TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS mute_roles (
    guild_id BIGINT PRIMARY KEY,
    role_id BIGINT NOT NULL
);



CREATE TABLE IF NOT EXISTS jail_settings (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    log_channel_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS mute_roles (
    guild_id BIGINT PRIMARY KEY,
    role_id BIGINT NOT NULL
);


CREATE TABLE IF NOT EXISTS channel_message_limits (
    channel_id BIGINT PRIMARY KEY,
    message_limit INT NOT NULL
);


CREATE TABLE IF NOT EXISTS blacklisted_users (
    user_id BIGINT PRIMARY KEY
);



   
CREATE TABLE IF NOT EXISTS snipe_messages (
    id SERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL,
    content TEXT,
    attachment_url TEXT,
    deleted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    channel_id BIGINT NOT NULL
);






-- MAYBE USE THIS IDK THIS IS FROM PRETEND
-- Table for storing guild-specific settings
CREATE TABLE guild_settings (
    guild_id BIGINT PRIMARY KEY,
    log_channel_id BIGINT,
    jail_role_id BIGINT,
    jail_channel_id BIGINT
);

-- Table for storing user-specific settings
CREATE TABLE user_settings (
    user_id BIGINT PRIMARY KEY,
    guild_id BIGINT,
    is_jailed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
);

-- Table for logging actions
CREATE TABLE action_logs (
    log_id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    action_type TEXT,
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id),
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
);

CREATE TABLE logging (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    guild_id BIGINT,
    user_id BIGINT,
    action TEXT,
    description TEXT,
    channels BIGINT, -- Assuming channels should be BIGINT as it stores IDs
    messages TEXT, -- Adding the missing 'messages' column
    UNIQUE(user_id), -- Unique constraint on user_id
    UNIQUE(channels), -- Unique constraint on channels
    UNIQUE(guild_id) -- Unique constraint on guild_id
);
  ALTER TABLE logging ADD COLUMN members BIGINT;

  CREATE TABLE edit_snipe_messages (
    id SERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL,
    content TEXT,
    attachment_url TEXT,
    edited_at TIMESTAMP NOT NULL,
    channel_id BIGINT NOT NULL
);


CREATE TABLE authorize (
    guild_id BIGINT PRIMARY KEY,
    buyer BIGINT NOT NULL,
    monthly BOOLEAN NOT NULL,
    transfers INT NOT NULL,
    billing TIMESTAMP,
    FOREIGN KEY (buyer) REFERENCES users(id)
);


    CREATE TABLE users (
        id BIGINT PRIMARY KEY,
        username TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );


CREATE TABLE whitelist (
    guild_id BIGINT,
    module TEXT,
    object_id BIGINT,
    mode TEXT,
    PRIMARY KEY (guild_id, module, object_id, mode),
    FOREIGN KEY (guild_id) REFERENCES antinuke_toggle(guild_id)
);

CREATE TABLE antinuke_toggle (
    guild_id BIGINT PRIMARY KEY,
    logs BIGINT
);

CREATE TABLE antinuke (
    guild_id BIGINT,
    module TEXT,
    punishment TEXT,
    threshold INTEGER,
    PRIMARY KEY (guild_id, module),
    FOREIGN KEY (guild_id) REFERENCES antinuke_toggle(guild_id)
);


CREATE TABLE reskin (
    user_id BIGINT PRIMARY KEY,
    avatar_url TEXT,
    name TEXT
);


   ALTER TABLE whitelist ADD COLUMN user_id BIGINT;


CREATE TABLE forced_nicknames (
    user_id BIGINT PRIMARY KEY,
    nickname TEXT NOT NULL
);


CREATE TABLE warnings (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    moderator_id VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);





CREATE TABLE mod (
    guild_id BIGINT PRIMARY KEY,
    is_enabled BOOLEAN DEFAULT FALSE
);


-- Table for storing warnings not in use rn
CREATE TABLE warnings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE whitelist (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    object_id BIGINT NOT NULL,
    mode VARCHAR(50),
    module VARCHAR(50),
    UNIQUE(guild_id, object_id, module)
);


CREATE TABLE fake_permissions (
    role_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    permissions JSONB,
    PRIMARY KEY (role_id, guild_id)
);


CREATE TABLE joint (
    guild_id BIGINT PRIMARY KEY,
    holder BIGINT NOT NULL
);


CREATE TABLE IF NOT EXISTS nodata (
    user_id BIGINT,
    guild_id BIGINT,
    state TEXT,
    other_column TEXT,
    PRIMARY KEY (user_id, guild_id)
);


CREATE TABLE IF NOT EXISTS antiinvite (
    guild_id BIGINT PRIMARY KEY
);



-- Table for storing guild-specific antiinvite settings
CREATE TABLE IF NOT EXISTS antiinvite (
    guild_id BIGINT PRIMARY KEY
);

-- Table for storing whitelist entries
CREATE TABLE IF NOT EXISTS whitelist (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    module TEXT NOT NULL,
    object_id BIGINT NOT NULL,
    mode TEXT NOT NULL,
    UNIQUE(guild_id, module, object_id, mode)
);

-- Example query to create indexes (optional but recommended for performance)
CREATE INDEX IF NOT EXISTS idx_whitelist_guild_id ON whitelist (guild_id);
CREATE INDEX IF NOT EXISTS idx_whitelist_module ON whitelist (module);
CREATE INDEX IF NOT EXISTS idx_whitelist_object_id ON whitelist (object_id);
CREATE INDEX IF NOT EXISTS idx_whitelist_mode ON whitelist (mode);



CREATE TABLE IF NOT EXISTS setme (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    log_channel_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS jail (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    roles JSONB NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);



CREATE TABLE autoroles (
    guild_id BIGINT PRIMARY KEY,
    role_id BIGINT
);




CREATE TABLE jail_logs (
    case_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE jail_logs ADD COLUMN action TEXT;


CREATE TABLE name_changes (
    user_id BIGINT,
    old_name VARCHAR(255),
    new_name VARCHAR(255),
    changed_at TIMESTAMP,
    PRIMARY KEY (user_id, changed_at)
);