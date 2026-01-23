import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.exception.write.WriteProcessException;
import org.apache.tsfile.read.common.Path;
import org.apache.tsfile.write.TsFileWriter;
import org.apache.tsfile.write.record.TSRecord;
import org.apache.tsfile.write.record.datapoint.DataPoint;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

public class TsFileExample {
    public static void main(String[] args) {
        // TODO: Replace with your actual file path
        String filePath = "example.tsfile";

        try {
            // Create TsFile writer
            File file = new File(filePath);
            TsFileWriter tsFileWriter = new TsFileWriter(file);

            // TODO: Define your schema - replace with your actual measurements
            List<IMeasurementSchema> schema = new ArrayList<>();
            schema.add(new MeasurementSchema("temperature", TSDataType.FLOAT));
            schema.add(new MeasurementSchema("humidity", TSDataType.FLOAT));
            schema.add(new MeasurementSchema("pressure", TSDataType.DOUBLE));

            // TODO: Replace with your device name
            String deviceId = "sensor_01";
            tsFileWriter.registerTimeseries(new Path(deviceId), schema);

            // Write sample data
            // TODO: Replace with your actual data writing logic
            for (int i = 0; i < 100; i++) {
                long timestamp = System.currentTimeMillis() + i * 1000; // 1 second intervals

                TSRecord tsRecord = new TSRecord(timestamp, deviceId);
                tsRecord.addTuple(DataPoint.getDataPoint(TSDataType.FLOAT, "temperature", 20.0f + i * 0.1f));
                tsRecord.addTuple(DataPoint.getDataPoint(TSDataType.FLOAT, "humidity", 50.0f + i * 0.5f));
                tsRecord.addTuple(DataPoint.getDataPoint(TSDataType.DOUBLE, "pressure", 1013.25 + i * 0.01));

                tsFileWriter.write(tsRecord);
            }

            // Close writer
            tsFileWriter.close();
            System.out.println("TsFile written successfully: " + filePath);

        } catch (WriteProcessException | IOException e) {
            System.err.println("Error writing TsFile: " + e.getMessage());
            e.printStackTrace();
        }
    }
}