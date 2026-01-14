CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL,
    role ENUM('pending','doctor','admin') DEFAULT 'pending'
);

#pending=arzt, wartet bis zertifikat geprüft wird
#doctor, darf patienten erfassen
#admin darf pending aerzte freischalten

CREATE TABLE aerzte (
    arztid INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    vorname VARCHAR(250) NOT NULL,
    nachname VARCHAR(250) NOT NULL,
    spital VARCHAR(250),
    telefonnummer VARCHAR(15),
    zertifikat_datei VARCHAR (255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE patienten (
    patientenid INT AUTO_INCREMENT PRIMARY KEY,
    arztid INT NOT NULL,
    telefonnummer VARCHAR(15) NOT NULL,
    spital VARCHAR(250) NOT NULL,
    vorname VARCHAR(250) NOT NULL,
    nachname VARCHAR(250) NOT NULL,
    gewicht FLOAT NOT NULL,
    groesse FLOAT NOT NULL,
    blutgruppe VARCHAR(4) NOT NULL,
    alterskategorie INT NOT NUll,
    alter_jahre INT NOT NULL,
    FOREIGN KEY (arztid) REFERENCES aerzte(arztid)
);

CREATE TABLE krankesorgan (
    krankesorganid INT AUTO_INCREMENT PRIMARY KEY,
    patientenid INT NOT NULL,
    organ VARCHAR(30) NOT NULL,
    dringlichkeit INT NOT NULL,
    FOREIGN KEY (patientenid) REFERENCES patienten(patientenid)
);

CREATE TABLE verstorbener (
    verstorbenenid INT AUTO_INCREMENT PRIMARY KEY,
    telefonnummerangehorige VARCHAR(15),
    spital VARCHAR (250),
    vorname VARCHAR(250),
    nachname VARCHAR(250),
    gewicht FLOAT NOT NULL,
    groesse FLOAT NOT NULL,
    blutgruppe VARCHAR(4) NOT NULL,
    alterskategorie INT NOT NULL
    
);


CREATE TABLE spenderorgane (
    spenderorganid INT AUTO_INCREMENT PRIMARY KEY,
    verstorbenenid INT NOT NULL,
    organ VARCHAR (30) NOT NULL,
    FOREIGN KEY (verstorbenenid) REFERENCES verstorbener (verstorbenenid)
);

CREATE TABLE zuteilung (
    zuteilungid INT AUTO_INCREMENT PRIMARY KEY,
    spenderorganid INT NOT NULL,
    krankesorganid INT NOT NULL,
    zeitpunkt DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('proposed','confirmed','rejected') DEFAULT 'proposed',
    FOREIGN KEY (spenderorganid) REFERENCES spenderorgane(spenderorganid),
    FOREIGN KEY (krankesorganid) REFERENCES krankesorgan(krankesorganid)
);

