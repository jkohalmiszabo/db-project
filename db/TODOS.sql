CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL
);

CREATE TABLE todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content VARCHAR(100),
    due DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE zustaendigerArzt (
    arztid INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(250) NOT NULL
    nachname VARCHAR(250) NOT NULL,
    spital VARCHAR(250),
    telefonnummer INT(10)
);

CREATE TABLE PatientEmpfanger (
    patientenid INT AUTO_INCREMENT PRIMARY KEY,
    telefonnummer INT(10) NOT NULL UNIQUE,
    spital VARCHAR(250) NOT NULL,
    vorname VARCHAR(250) NOT NULL,
    nachname VARCHAR(250) NOT NULL,
    gewicht FLOAT(4) NOT NULL,
    groesse FLOAT(4) NOT NULL,
    blutgruppe VARCHAR(4) NOT NULL,
    alterskategorie INT(2) NOT NUll,
    alter. INT(3) NOT NULL
    FOREIGN KEY (arztid) REFERENCES zustaendigerArzt(arztid)
);

CREATE TABLE krankesOrgan (
    FOREIGN KEY (patientenid) REFERENCES PatientEmpfanger(patientenid),
    organ VARCHAR(30) NOT NULL,
    dringlichkeit INT(2) NOT NULL
);

CREATE TABLE Spenderorgane (
    organ VARCHAR (30) NOT NULL,
    FOREIGN KEY (verstorbenenid) REFERENCES VerstorbenerHirntoter (verstorbenenid)
);

CREATE TABLE VerstorbenerHirntoter (
    verstorbenenid INT AUTO-INCREMENT PRIMARY KEY,
    telefonnummerangehorige INT(10),
    spital VARCHAR (250),
    vorname VARCHAR(250),
    nachname VARCHAR(250),
    gewicht FLOAT(4) NOT NULL,
    groesse FLOAT(4) NOT NULL,
    blutgruppe VARCHAR(4) NOT NULL,
    alterskategorie INT(2) NOT NUll
);

INSERT INTO zustaendigerArzt(vorname,nachname,spital,telefonnummer) VALUES
('Joseph', 'Müller',' Uniklinik Zürich',0791234567),
('Anna','Schneider',' Uniklinik Luzern',0791234568);

INSERT INTO PatientEmpfanger (telefonnummer,spital,vorname,nachname,gewicht,groesse, blutgruppe,alterskategorie,alter.) VALUES
(0791234569, 'Triemlispital', 'Thomas', 'Schneider',70.0,1.87, AB, 4,30);

INSERT INTO PatientEmpfanger (telefonnummer,spital,vorname,nachname,gewicht,groesse) VALUES
(0791234569', 'Triemlispital', 'Thomas', 'Schneider',70.0, 1.78);
