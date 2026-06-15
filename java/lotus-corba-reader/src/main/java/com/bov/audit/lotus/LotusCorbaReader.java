package com.bov.audit.lotus;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Vector;

import lotus.domino.Database;
import lotus.domino.DateTime;
import lotus.domino.Document;
import lotus.domino.NotesException;
import lotus.domino.NotesFactory;
import lotus.domino.Session;
import lotus.domino.View;
import lotus.domino.ViewEntry;
import lotus.domino.ViewNavigator;

public final class LotusCorbaReader {
    private static final String VERSION = "1.0.0";

    private LotusCorbaReader() {
    }

    public static void main(String[] args) {
        try {
            Map<String, String> options = parseArgs(args);
            if (options.containsKey("help")) {
                printHelp();
                return;
            }
            if (options.containsKey("version")) {
                System.out.println(VERSION);
                return;
            }
            run(options);
        } catch (Exception exception) {
            System.err.println("Lotus CORBA extraction failed: " + sanitizeMessage(exception));
            System.exit(1);
        }
    }

    private static void run(Map<String, String> options) throws Exception {
        String iorFile = required(options, "ior-file");
        String username = required(options, "username");
        String password = required(options, "password");
        String databasePath = required(options, "database");
        String viewName = required(options, "view");
        String outputPath = required(options, "output");
        String dataset = required(options, "dataset");
        String replicaId = optional(options, "replica-id");
        String server = optional(options, "server");
        List<String> columns = parseColumns(required(options, "columns"));

        String ior = new String(Files.readAllBytes(Paths.get(iorFile)), StandardCharsets.UTF_8).trim();
        if (ior.isEmpty()) {
            throw new IllegalArgumentException("IOR file is empty.");
        }

        Session session = null;
        Database database = null;
        View view = null;
        ViewNavigator navigator = null;
        ViewEntry entry = null;

        File outputFile = new File(outputPath);
        File parent = outputFile.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(outputFile), StandardCharsets.UTF_8))) {
            session = NotesFactory.createSessionWithIOR(ior, username, password);
            database = session.getDatabase(server == null ? "" : server, databasePath);
            if (database == null || !database.isOpen()) {
                throw new IllegalStateException("Could not open configured Domino database.");
            }
            view = database.getView(viewName);
            if (view == null) {
                throw new IllegalStateException("Could not open configured Domino view.");
            }

            navigator = view.createViewNav();
            entry = navigator.getFirst();
            long rowNumber = 0;
            while (entry != null) {
                ViewEntry next = null;
                try {
                    rowNumber++;
                    next = navigator.getNext(entry);
                    writer.write(toJsonRow(
                            entry,
                            columns,
                            dataset,
                            databasePath,
                            viewName,
                            replicaId,
                            rowNumber));
                    writer.newLine();
                } finally {
                    recycle(entry);
                    entry = next;
                }
            }
        } finally {
            recycle(entry);
            recycle(navigator);
            recycle(view);
            recycle(database);
            recycle(session);
        }
    }

    private static String toJsonRow(
            ViewEntry entry,
            List<String> columns,
            String dataset,
            String database,
            String view,
            String replicaId,
            long rowNumber) throws NotesException {
        Vector<?> values = entry.getColumnValues();
        StringBuilder fields = new StringBuilder("{");
        for (int index = 0; index < columns.size(); index++) {
            if (index > 0) {
                fields.append(',');
            }
            Object value = index < values.size() ? values.get(index) : null;
            fields.append(quote(columns.get(index))).append(':').append(jsonValue(value));
        }
        fields.append('}');

        String noteId = safeString(entry.getNoteID());
        String universalId = null;
        String createdDate = null;
        String lastModifiedDate = null;
        Document document = null;
        DateTime created = null;
        DateTime modified = null;
        try {
            if (entry.isDocument()) {
                document = entry.getDocument();
                if (document != null) {
                    universalId = safeString(document.getUniversalID());
                    created = document.getCreated();
                    modified = document.getLastModified();
                    createdDate = created == null ? null : safeString(created.getLocalTime());
                    lastModifiedDate = modified == null ? null : safeString(modified.getLocalTime());
                }
            }
        } finally {
            recycle(created);
            recycle(modified);
            recycle(document);
        }

        StringBuilder row = new StringBuilder("{");
        appendProperty(row, "dataset", dataset, false);
        appendProperty(row, "database", database, true);
        appendProperty(row, "view", view, true);
        appendProperty(row, "replica_id", replicaId, true);
        appendProperty(row, "extracted_at", Instant.now().toString(), true);
        row.append(",\"row_number\":").append(rowNumber);
        appendProperty(row, "note_id", noteId, true);
        appendProperty(row, "universal_id", universalId, true);
        appendProperty(row, "created_date", createdDate, true);
        appendProperty(row, "last_modified_date", lastModifiedDate, true);
        row.append(",\"fields\":").append(fields).append('}');
        return row.toString();
    }

    private static void appendProperty(
            StringBuilder builder,
            String name,
            String value,
            boolean prependComma) {
        if (prependComma) {
            builder.append(',');
        }
        builder.append(quote(name)).append(':');
        builder.append(value == null ? "null" : quote(value));
    }

    private static String jsonValue(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof Number || value instanceof Boolean) {
            return String.valueOf(value);
        }
        return quote(String.valueOf(value));
    }

    private static String quote(String value) {
        String escaped = value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\r", "\\r")
                .replace("\n", "\\n")
                .replace("\t", "\\t");
        return "\"" + escaped + "\"";
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> options = new HashMap<String, String>();
        for (int index = 0; index < args.length; index++) {
            String argument = args[index];
            if ("--help".equals(argument)) {
                options.put("help", "true");
                continue;
            }
            if ("--version".equals(argument)) {
                options.put("version", "true");
                continue;
            }
            if (!argument.startsWith("--") || index + 1 >= args.length) {
                throw new IllegalArgumentException("Invalid command arguments.");
            }
            options.put(argument.substring(2), args[++index]);
        }
        return options;
    }

    private static List<String> parseColumns(String rawColumns) {
        List<String> columns = new ArrayList<String>();
        for (String column : rawColumns.split(",")) {
            String normalized = column.trim();
            if (!normalized.isEmpty()) {
                columns.add(normalized);
            }
        }
        if (columns.isEmpty()) {
            throw new IllegalArgumentException("At least one column is required.");
        }
        return columns;
    }

    private static String required(Map<String, String> options, String name) {
        String value = options.get(name);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Missing required option --" + name);
        }
        return value;
    }

    private static String optional(Map<String, String> options, String name) {
        String value = options.get(name);
        return value == null || value.trim().isEmpty() ? null : value;
    }

    private static String safeString(String value) {
        return value == null || value.isEmpty() ? null : value;
    }

    private static String sanitizeMessage(Exception exception) {
        if (exception instanceof IllegalArgumentException
                || exception instanceof IllegalStateException) {
            return exception.getMessage();
        }
        return exception.getClass().getSimpleName();
    }

    private static void recycle(lotus.domino.Base object) {
        if (object != null) {
            try {
                object.recycle();
            } catch (NotesException ignored) {
                // Best-effort cleanup.
            }
        }
    }

    private static void printHelp() {
        System.out.println(
                "Lotus CORBA Reader " + VERSION + "\n"
                        + "Required: --ior-file --username --password --database --view "
                        + "--output --columns --dataset\n"
                        + "Optional: --server --replica-id --help --version");
    }
}
