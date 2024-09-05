-- Dashboard
-- Add task to wrike

-- Count of parcels with duplicate pins
SELECT foo.pin, foo.count
   FROM ( SELECT parcel.pin,
            count(*) AS count
           FROM dor.parcel_rev_evw parcel
          WHERE parcel.status = ANY (ARRAY[1, 3])
          GROUP BY parcel.pin) foo
  WHERE foo.count > 1 and foo.pin is not null
  order by foo.count desc , foo.pin;
  
-- The parcels with null pins so they can easily use the app
select pre.addr_std , pre.mapreg , count(*)
from dor.parcel_rev_evw pre 
WHERE pre.status = ANY (ARRAY[1, 3]) and pre.pin is null
group by pre.addr_std , pre.mapreg 
order by count(*) desc , addr_std , mapreg;

-- 6 where addr_std is null and pin is null
select pre.addr_std , pre.mapreg , count(*)
from dor.parcel_rev_evw pre 
WHERE pre.status = ANY (ARRAY[1, 3]) and pre.pin is null
group by pre.addr_std , pre.mapreg 
having addr_std is null

-- 9,024 addr_std is null in total
select count(*)
from (select pre.addr_std , pre.mapreg , count(*)
from dor.parcel_rev_evw pre 
WHERE pre.status = ANY (ARRAY[1, 3])
group by pre.addr_std , pre.mapreg 
having addr_std is null and mapreg is not null
order by count(*) desc) t
;

-- Button Refresh for the dashboard

-- 