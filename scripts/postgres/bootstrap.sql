-- Run as a PostgreSQL administrator. Replace the sample passwords first.
CREATE ROLE hacktitlan_owner NOLOGIN;
CREATE ROLE hacktitlan_app LOGIN PASSWORD 'CHANGE_ME_APP';
CREATE ROLE hacktitlan_migrator LOGIN PASSWORD 'CHANGE_ME_MIGRATOR';
CREATE DATABASE hacktitlan OWNER hacktitlan_owner;
CREATE DATABASE hacktitlan_test OWNER hacktitlan_owner;

\connect hacktitlan
GRANT CONNECT ON DATABASE hacktitlan TO hacktitlan_app, hacktitlan_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO hacktitlan_migrator;
GRANT USAGE ON SCHEMA public TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hacktitlan_app;

\connect hacktitlan_test
GRANT CONNECT ON DATABASE hacktitlan_test TO hacktitlan_app, hacktitlan_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO hacktitlan_migrator;
GRANT USAGE ON SCHEMA public TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO hacktitlan_app;
ALTER DEFAULT PRIVILEGES FOR ROLE hacktitlan_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hacktitlan_app;

