import api from "./api"; // Import the Axios instance

// Helper to safely access nested data and convert to number
const getSensorValue = (responseData, path = "data.value", defaultValue = 0) => {
  let current = responseData;
  const keys = path.split('.');
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return defaultValue;
    }
  }
  const numValue = Number(current);
  return isNaN(numValue) ? defaultValue : numValue;
};

// Helper to safely access nested string data
const getSensorString = (responseData, path = "data.feed_id", defaultValue = "N/A") => {
  let current = responseData;
  const keys = path.split('.');
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return defaultValue;
    }
  }
  return String(current) || defaultValue;
};

// Helper to safely access nested date data
const getSensorDate = (responseData, path = "data.created_at", defaultValue = new Date().toISOString()) => {
  let current = responseData;
  const keys = path.split('.');
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return defaultValue;
    }
  }
  const date = new Date(current);
  return isNaN(date.getTime()) ? defaultValue : date.toISOString();
};

export const fetchSensorData = async () => {
  try {
    const [tempRes, moistureRes, lightRes, soilRes] = await Promise.all([
      api.get("/dht-temp/latest"),
      api.get("/dht-moisure/latest"),      // CHECK TYPO: Should it be /dht-moisture/latest ?
      api.get("/light-sensor/latest"),
      api.get("/soil-moisture/latest"), // CHECK TYPO: Should it be /soil-moisture/latest ?
    ]);

    return {
      temperature: {
        value: getSensorValue(tempRes.data, "data.value"),
        feedId: getSensorString(tempRes.data, "data.feed_id"),
        createdAt: getSensorDate(tempRes.data, "data.created_at"),
      },
      moisture: { // Air moisture
        value: getSensorValue(moistureRes.data, "data.value"),
        feedId: getSensorString(moistureRes.data, "data.feed_id"),
        createdAt: getSensorDate(moistureRes.data, "data.created_at"),
      },
      light: {
        value: getSensorValue(lightRes.data, "data.value"),
        feedId: getSensorString(lightRes.data, "data.feed_id"),
        createdAt: getSensorDate(lightRes.data, "data.created_at"),
      },
      soil: { // Soil moisture
        value: getSensorValue(soilRes.data, "data.value"),
        feedId: getSensorString(soilRes.data, "data.feed_id"),
        createdAt: getSensorDate(soilRes.data, "data.created_at"),
      },
    };
  } catch (error) {
    console.error("Error fetching sensor data:", error.response?.data || error.message);
    // Return default structure on error to prevent crashes in consuming components
    const defaultData = { value: 0, feedId: "N/A", createdAt: new Date().toISOString() };
    return { temperature: defaultData, moisture: defaultData, light: defaultData, soil: defaultData };
  }
};

export const fetchChartData = async (lastHours = 12) => {
  try {
    const [tempRes, moistureRes, lightRes, soilRes] = await Promise.all([
      api.get(`/dht-temp/history?lastHours=${lastHours}`),
      api.get(`/dht-moisure/history?lastHours=${lastHours}`),    // CHECK TYPO
      api.get(`/light-sensor/history?lastHours=${lastHours}`),
      api.get(`/soil-moisture/history?lastHours=${lastHours}`), // CHECK TYPO
    ]);

    const transformData = (response) => {
      const rawData = response.data?.data || [];
      // Assuming backend returns newest first, take up to `lastHours` equivalent (approx) and reverse for chronological chart
      // This example takes the first 12 from the response as per original logic, assuming backend handles `lastHours`
      const sliced = (rawData.length > 12 ? rawData.slice(0, 12) : rawData).reverse();


      return {
        labels: sliced.map((item) =>
          new Date(item.created_at).toLocaleTimeString("vi-VN", { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' })
        ),
        values: sliced.map((item) => getSensorValue(item, "value")), // Use helper here too
      };
    };
    
    // response.data comes from axios, so the actual data is inside response.data.data from backend
    return {
      temperature: transformData(tempRes.data), // Pass tempRes.data, not tempRes
      moisture: transformData(moistureRes.data),
      light: transformData(lightRes.data),
      soil: transformData(soilRes.data),
    };
  } catch (error) {
    console.error("Error fetching chart data:", error.response?.data || error.message);
    // Return default structure on error
    const defaultChart = { labels: [], values: [] };
    return { temperature: defaultChart, moisture: defaultChart, light: defaultChart, soil: defaultChart };
  }
};