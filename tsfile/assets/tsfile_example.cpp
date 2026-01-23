#include <writer/tsfile_table_writer.h>
#include <reader/tsfile_reader.h>
#include <iostream>
#include <string>
#include <vector>

int main() {
    // Initialize TsFile library
    storage::libtsfile_init();

    std::string filename = "example_cpp.tsfile";

    try {
        // ===============================
        // WRITING DATA
        // ===============================

        // Create write file
        storage::WriteFile writeFile;
        int flags = O_WRONLY | O_CREAT | O_TRUNC;
#ifdef _WIN32
        flags |= O_BINARY;
#endif
        writeFile.create(filename, flags, 0666);

        // TODO: Define your table schema - replace with your measurements
        auto* schema = new storage::TableSchema("sensors", {
            // Tag columns (device identifiers)
            common::ColumnSchema("device_id", common::STRING,
                               common::UNCOMPRESSED, common::PLAIN,
                               common::ColumnCategory::TAG),

            // Field columns (actual measurements)
            common::ColumnSchema("temperature", common::DOUBLE,
                               common::UNCOMPRESSED, common::PLAIN,
                               common::ColumnCategory::FIELD),
            common::ColumnSchema("humidity", common::DOUBLE,
                               common::UNCOMPRESSED, common::PLAIN,
                               common::ColumnCategory::FIELD),
            common::ColumnSchema("pressure", common::DOUBLE,
                               common::UNCOMPRESSED, common::PLAIN,
                               common::ColumnCategory::FIELD)
        });

        // Create writer
        storage::TsFileTableWriter writer(&writeFile, schema);

        // Create tablet for batch writing
        int batchSize = 1000;
        auto tablet = new storage::Tablet(schema, batchSize);

        // TODO: Replace with your actual data generation logic
        std::cout << "Writing data to " << filename << "..." << std::endl;

        for (int i = 0; i < batchSize; i++) {
            int64_t timestamp = (int64_t)time(nullptr) * 1000 + i * 1000; // milliseconds

            // Add timestamp
            tablet->add_timestamp(i, timestamp);

            // Add device ID
            std::string deviceId = "sensor_" + std::to_string((i % 10) + 1);
            tablet->add_value("device_id", i, deviceId);

            // Add measurements
            tablet->add_value("temperature", i, 20.0 + (i % 50) * 0.1);
            tablet->add_value("humidity", i, 50.0 + (i % 30) * 0.5);
            tablet->add_value("pressure", i, 1013.25 + (i % 20) * 0.01);
        }

        // Write the tablet
        writer.write_tablet(tablet);
        writer.close();

        std::cout << "✅ Successfully wrote " << batchSize << " records to " << filename << std::endl;

        // ===============================
        // READING DATA
        // ===============================

        // Open file for reading
        storage::ReadFile readFile;
        readFile.open(filename);

        // Create reader
        storage::TsFileReader reader;
        reader.open(&readFile);

        // Get table names
        std::vector<std::string> tableNames = reader.get_table_names();
        std::cout << "\nFound " << tableNames.size() << " table(s) in TsFile:" << std::endl;

        for (const auto& tableName : tableNames) {
            std::cout << "  - " << tableName << std::endl;

            // TODO: Customize your query conditions
            // Read all data from the table
            storage::QueryDataSet result = reader.read_table(tableName);

            int recordCount = 0;
            std::cout << "Reading data from table '" << tableName << "':" << std::endl;

            while (result.has_next() && recordCount < 10) { // Show first 10 records
                storage::RowRecord record = result.next();

                // TODO: Process record data according to your needs
                std::cout << "  Record " << recordCount + 1 << ": timestamp="
                         << record.get_timestamp() << std::endl;

                recordCount++;
            }

            std::cout << "  (showing first 10 records)" << std::endl;
        }

        reader.close();

        // Cleanup
        delete tablet;
        delete schema;

        std::cout << "\n✅ TsFile operations completed successfully!" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}