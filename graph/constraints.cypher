CREATE CONSTRAINT character_name_unique
FOR (c:Character)
REQUIRE c.name IS UNIQUE;
