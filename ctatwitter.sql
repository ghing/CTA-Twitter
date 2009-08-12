CREATE TABLE ctatwitter (
    messageid TEXT PRIMARY KEY NOT NULL,
    createdat TEXT,
    recipientid TEXT,
    recipientscreenname TEXT,
    recipientname TEXT,
    campaignid TEXT,
    emailtype TEXT,
    senderid TEXT,
    sendername TEXT,
    senderscreenname TEXT,
    directmessageid TEXT
);
