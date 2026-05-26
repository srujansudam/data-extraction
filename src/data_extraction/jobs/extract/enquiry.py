from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


# TODO: Validate that start_time, terminal_id, and branch_code exist on the client DB in
# fcbov.smtb_sms_log and fcbov.smtb_sms_log_hist.
ENQUIRY_SQL = """
WITH log_rows AS
(
    SELECT
        sm.sequence_no,
        sm.user_id,
        sm.function_id,
        sm.start_time,
        sm.terminal_id,
        sm.branch_code,
        'CURR' AS src
    FROM fcbov.smtb_sms_log sm
    WHERE sm.function_id IN ('STDCIF', 'STDCUSUM')

    UNION ALL

    SELECT
        smh.sequence_no,
        smh.user_id,
        smh.function_id,
        smh.start_time,
        smh.terminal_id,
        smh.branch_code,
        'HIST' AS src
    FROM fcbov.smtb_sms_log_hist smh
    WHERE smh.function_id IN ('STDCIF', 'STDCUSUM')
),
action_rows AS
(
    SELECT
        ac.sequence_no,
        ac.action_sequence_no,
        ac.req_time,
        ac.action,
        ac.pkvals,
        ac.description AS error_msg,
        'CURR' AS src
    FROM fcbov.smtb_sms_action_log ac
    WHERE ac.action = 'EXECUTEQUERY'
      AND ac.req_time >= TO_DATE(:1, 'YYYY-MM-DD')
      AND ac.req_time <  TO_DATE(:2, 'YYYY-MM-DD')
      AND SUBSTR(TRIM(ac.pkvals), -1) IN ('M', 'N')

    UNION ALL

    SELECT
        ach.sequence_no,
        ach.action_sequence_no,
        ach.req_time,
        ach.action,
        ach.pkvals,
        ach.description AS error_msg,
        'HIST' AS src
    FROM fcbov.smtb_sms_action_log_hist ach
    WHERE ach.action = 'EXECUTEQUERY'
      AND ach.req_time >= TO_DATE(:1, 'YYYY-MM-DD')
      AND ach.req_time <  TO_DATE(:2, 'YYYY-MM-DD')
      AND SUBSTR(TRIM(ach.pkvals), -1) IN ('M', 'N')
)
SELECT
    l.user_id AS user_code,
    l.function_id AS function_id,
    l.start_time AS start_time,
    a.req_time AS action_time,
    l.terminal_id AS terminal_id,
    l.branch_code AS branch_code,
    fd.description AS description,
    a.action AS action,
    a.pkvals AS pkvals,
    fd.main_menu || ' -> ' || fd.sub_menu_1 || ' -> ' || fd.sub_menu_2 AS breadcrumbs,
    a.error_msg AS error_msg
FROM log_rows l
JOIN action_rows a
    ON a.sequence_no = l.sequence_no
   AND a.src = l.src
LEFT JOIN fcbov.smtb_function_description fd
    ON fd.function_id = l.function_id
"""


class EnquiryExtractionJob(BaseExtractionJob):
    job_name = "enquiry"
    source_system = "flexcube"
    target_table = "enquiry"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        if window_start is None or window_end is None:
            raise ValueError("enquiry extraction requires window_start and window_end.")

        start_date = window_start[:10]
        end_date = window_end[:10]
        rows = self.source_client.query_all(ENQUIRY_SQL, [start_date, end_date])

        insert_rows = [
            [
                row.get("user_code"),
                row.get("function_id"),
                row.get("start_time"),
                row.get("action_time"),
                row.get("terminal_id"),
                row.get("branch_code"),
                row.get("description"),
                row.get("action"),
                row.get("pkvals"),
                row.get("breadcrumbs"),
                row.get("error_msg"),
            ]
            for row in rows
        ]

        if not insert_rows:
            return JobResult(
                rows_extracted=len(rows),
                rows_inserted=0,
                rows_updated=0,
                rows_rejected=0,
            )

        for row in insert_rows:
            self.db.execute(
                """
                DELETE FROM enquiry
                WHERE user_code = ?
                    AND function_id = ?
                    AND start_time = ?
                """,
                row[:3],
            )

        self.db.execute_many(
            """
            INSERT INTO enquiry (
                user_code,
                function_id,
                start_time,
                action_time,
                terminal_id,
                branch_code,
                description,
                action,
                pkvals,
                breadcrumbs,
                error_msg
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return JobResult(
            rows_extracted=len(rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )
