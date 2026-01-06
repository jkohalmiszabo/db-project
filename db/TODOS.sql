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
    Arzt-ID INT AUTO_INCREMENT PRIMARY KEY,
    Vorname VARCHAR(250) NOT NULL
    Nachname VARCHAR(250) NOT NULL,
    Spital VARCHAR(250),
    Telefonnummer INT(10)
);

CREATE TABLE PatientEmpfänger (
    Patienten-ID INT AUTO_INCREMENT PRIMARY KEY,
    Telefonnummer INT(10) NOT NULL UNIQUE,
    Spital VARCHAR(250) NOT NULL,
    Vorname VARCHAR(250) NOT NULL,
    Nachname VARCHAR(250) NOT NULL,
    Gewicht(kg) FLOAT(4) NOT NULL,
    Koerpergroesse(m) FLOAT(4) NOT NULL,
    Blutgruppe VARCHAR(4) NOT NULL,
    Alterskategorie INT(2) NOT NUll,
    Alter INT(3) NOT NULL
    FOREIGN KEY (Arzt-ID) REFERENCES zuständiger Arzt(Arzt-ID)
);

CREATE TABLE krankesOrgan (
    FOREIGN KEY (Patienten-ID) REFERENCES Patient/Empfänger(Patienten-ID),
    ORGAN VARCHAR(30) NOT NULL,
    Dringlichkeit INT(2) NOT NULL
);

CREATE TABLE Spenderorgane (
    Organ VARCHAR (30) NOT NULL,
    FOREIGN KEY (Verstorbenen-ID) REFERENCES Verstorbener/Hirntoter (Verstorbenen-ID)
);

CREATE TABLE VerstorbenerHirntoter (
    Verstorbenen-ID INT AUTO-INCREMENT PRIMARY KEY,
    Telefonnummer eines Angehörigen INT(10),
    Spital VARCHAR (250),
    Vorname VARCHAR(250),
    Nachname VARCHAR(250),
    Gewicht(kg) FLOAT(4) NOT NULL,
    Körpergrösse(m) FLOAT(4) NOT NULL,
    Blutgruppe VARCHAR(4) NOT NULL,
    Alterskategorie INT(2) NOT NUll
);

INSERT INTO zustaendigerArzt(Vorname,Nachname,Spital,Telefonnummer) VALUES
('Joseph', 'Müller',' Uniklinik Zürich','0791234567'),
('Anna','Schneider',' Uniklinik Luzern','0791234568');

INSERT INTO PatientEmpfänger (Telefonnummer,Spital,Vorname,Nachname,Gewicht(kg),Koerpergroesse)