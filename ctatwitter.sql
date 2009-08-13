CREATE TABLE emails (
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

CREATE TABLE direct_messages (
    directmessageid TEXT PRIMARY KEY NOT NULL,
    message TEXT
);
