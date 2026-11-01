-- Earthquake ETL Pipeline — analysis queries (all executed against data/quakes.db)
-- Dataset: USGS Magnitude 2.5+ earthquakes, past 7 days (rolling feed).

-- Q1. How many events per magnitude band?
SELECT mag_band, COUNT(*) AS events
FROM earthquakes
GROUP BY mag_band
ORDER BY MIN(mag);

-- Q2. The 10 strongest earthquakes this week
SELECT mag, place, occurred_at_utc, depth_km
FROM earthquakes
ORDER BY mag DESC
LIMIT 10;

-- Q3. Earthquakes per day (UTC)
SELECT date(occurred_at_utc) AS day, COUNT(*) AS events,
       ROUND(MAX(mag), 1) AS strongest_that_day
FROM earthquakes
GROUP BY day
ORDER BY day;

-- Q4. The 5 deepest earthquakes (deep quakes behave very differently)
SELECT mag, place, depth_km, occurred_at_utc
FROM earthquakes
ORDER BY depth_km DESC
LIMIT 5;

-- Q5. The 5 most-felt earthquakes (human impact, not just size)
SELECT mag, place, felt, occurred_at_utc
FROM earthquakes
WHERE felt > 0
ORDER BY felt DESC
LIMIT 5;

-- Q6. How many events carried a tsunami flag?
SELECT COUNT(*) AS tsunami_flagged
FROM earthquakes
WHERE tsunami = 1;

-- Q7. Busiest regions: event count and average magnitude
SELECT region, COUNT(*) AS events, ROUND(AVG(mag), 2) AS avg_mag,
       ROUND(MAX(mag), 1) AS strongest
FROM earthquakes
GROUP BY region
ORDER BY events DESC
LIMIT 10;

-- Q8. Daily count vs the week's daily average (window function)
SELECT day, events,
       ROUND(AVG(events) OVER (), 1) AS weekly_daily_avg,
       events - ROUND(AVG(events) OVER (), 1) AS vs_average
FROM (SELECT date(occurred_at_utc) AS day, COUNT(*) AS events
      FROM earthquakes GROUP BY day)
ORDER BY day;
