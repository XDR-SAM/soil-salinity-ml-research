# Workbook audit

- 2024, `Soil_Salinity_Data_BD032024`: header on row 3; workbook headers ['ID', 'SAMPLE_NO', 'Latitude', 'Longitude', 'Electrical_Conductivity_EC(mS/cm)', 'Sample_Typ', 'Collection_Date', 'Team']; blank rows []; copyright footer rows [166].
- 2025, `Soil_Salinity_Data_BD042025`: header on row 3; workbook headers ['ID', 'SAMPLE_NO', 'Latitude', 'Longitude', 'Electrical_Conductivity_EC(mS/cm)', 'Sample_Type', 'Collection_Date', 'Team']; blank rows []; copyright footer rows [191].

**349 populated field rows; 349 eligible records.** No salinity outlier trimming.

Blank formatted rows are distinct from populated samples. The laboratory contact rows are skipped and never exported.

## 2024

- Eligible 162 of 162. Missing original values: {'original_id': 0, 'sample_id': 0, 'lat': 0, 'lon': 0, 'ec': 0, 'sample_type': 0, 'date': 0, 'team': 0}.
- Dates 2024-03-02 to 2024-03-06 (0 unparsed/missing; 0 parsed outside source year).
- Latitude 22.219537 to 23.140740; longitude 88.906570 to 89.644310.
- EC five-number summary [0.0505, 0.3208, 1.14, 2.1887, 9.085] mS/cm. Mean 1.5175, sample SD 1.5389 mS/cm.
- Duplicate IDs beyond first: original ID 0, sample number 0. Exact coordinate pairs: 0; pairs within 20 m: 0.

## 2025

- Eligible 187 of 187. Missing original values: {'original_id': 0, 'sample_id': 0, 'lat': 0, 'lon': 0, 'ec': 0, 'sample_type': 0, 'date': 0, 'team': 0}.
- Dates 2025-04-11 to 2025-04-14 (0 unparsed/missing; 0 parsed outside source year).
- Latitude 22.214545 to 22.929983; longitude 88.936053 to 89.580165.
- EC five-number summary [0.1213, 0.5092, 1.748, 4.05, 10.5] mS/cm. Mean 2.5330, sample SD 2.4710 mS/cm.
- Duplicate IDs beyond first: original ID 0, sample number 0. Exact coordinate pairs: 0; pairs within 20 m: 1.

## Cross-year geography

Exact cross-year coordinate pairs: 0. Pairs within 20 m: 0. Median distance to nearest site in the other campaign: 3.07 km from 2024 and 2.98 km from 2025.

Location, month and year vary together. The campaign EC distributions cannot identify within-site salinity change. Coordinates use WGS84 degrees, projected to WGS84 / UTM zone 45N (EPSG:32645) for distances.
