# Lotus CORBA Reader

Java 8-compatible CLI reader for Domino DIIOP/CORBA views.

## Client-Supplied Dependencies

The repository does not include:

- `notes.jar`
- `ncso.jar`
- `diiop_ior.txt`
- Domino credentials

BOV/client IT must place the approved Domino jars under `java/lib/` before building:

```text
java/
  lib/
    notes.jar
    ncso.jar
  lotus-corba-reader/
```

Use a client-approved Java 8 runtime. IBM Semeru/OpenJ9 8 is preferred when approved.

## Build

From `java/lotus-corba-reader`:

```powershell
gradle clean build
```

Output:

```text
build/libs/lotus-corba-reader.jar
```

For deployment, copy the built jar to:

```text
java/lotus-corba-reader/lotus-corba-reader.jar
```

## Runtime

The Python application invokes the main class with a classpath containing:

- the reader jar
- `notes.jar`
- `ncso.jar`

The reader accepts:

```text
--ior-file
--username
--password
--database
--view
--output
--columns
--dataset
--server
--replica-id
--help
--version
```

Output is UTF-8 NDJSON, one row per Domino view entry. The password is never printed.
