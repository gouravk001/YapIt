import { useEffect, useState } from "react";
import { getNotes } from "../api/client";

// Far more than anyone records in a day; keeps the request bounded.
const TODAY_LIMIT = 200;

function startOfTodayIso() {
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  return midnight.toISOString();
}

export function useTodayNotes(refreshKey) {
  const [notes, setNotes] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error

  useEffect(() => {
    let ignore = false;
    getNotes({ date_from: startOfTodayIso(), limit: TODAY_LIMIT })
      .then((data) => {
        if (ignore) return;
        setNotes(data || []);
        setStatus("ready");
      })
      .catch(() => !ignore && setStatus("error"));
    return () => {
      ignore = true;
    };
  }, [refreshKey]);

  return { notes, status };
}
