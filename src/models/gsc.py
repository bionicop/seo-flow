"""
Pydantic models for Google Search Console API responses.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, HttpUrl, computed_field


class GSCMetric(BaseModel):
    """Single Google Search Console metric row."""

    query: str = Field(description="Search query")
    page: HttpUrl | None = Field(default=None, description="Page URL")
    clicks: int = Field(ge=0, description="Number of clicks")
    impressions: int = Field(ge=0, description="Number of impressions")
    ctr: float = Field(ge=0.0, le=1.0, description="Click-through rate (0-1)")
    position: float = Field(ge=0.0, description="Average position")
    metric_date: date | None = Field(default=None, description="Date of the metric")
    country: str | None = Field(default=None, description="Country code (e.g., 'ind')")
    device: str | None = Field(
        default=None, description="Device type: mobile, desktop, tablet"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "python async",
                "page": "https://example.com/python-async/",
                "clicks": 45,
                "impressions": 1200,
                "ctr": 0.0375,
                "position": 5.2,
                "metric_date": "2026-01-07",
                "country": "ind",
                "device": "mobile",
            }
        }

    @computed_field
    @property
    def ctr_percentage(self) -> float:
        """CTR as percentage (0-100)."""
        return round(self.ctr * 100, 2)

    @computed_field
    @property
    def is_first_page(self) -> bool:
        """Check if average position is on first page (<=10)."""
        return self.position <= 10


class GSCResponse(BaseModel):
    """Google Search Console API response."""

    site_url: HttpUrl = Field(description="Site URL in GSC")
    metrics: list[GSCMetric] = Field(default=[], description="Performance metrics")
    start_date: date = Field(description="Start date of data range")
    end_date: date = Field(description="End date of data range")
    total_queries: int = Field(ge=0, default=0, description="Total unique queries")
    total_clicks: int = Field(ge=0, default=0, description="Total clicks")
    total_impressions: int = Field(ge=0, default=0, description="Total impressions")
    average_ctr: float = Field(ge=0.0, le=1.0, default=0.0, description="Average CTR")
    average_position: float = Field(ge=0.0, default=0.0, description="Average position")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "site_url": "https://bionicop.github.io/Digital-Garden/",
                "metrics": [],
                "start_date": "2026-01-01",
                "end_date": "2026-01-07",
                "total_queries": 45,
                "total_clicks": 120,
                "total_impressions": 3500,
                "average_ctr": 0.034,
                "average_position": 12.5,
                "fetched_at": "2026-01-08T00:00:00Z",
            }
        }

    @computed_field
    @property
    def average_ctr_percentage(self) -> float:
        """Average CTR as percentage."""
        return round(self.average_ctr * 100, 2)

    @computed_field
    @property
    def days_in_range(self) -> int:
        """Number of days in the data range."""
        return (self.end_date - self.start_date).days + 1

    @classmethod
    def from_api_response(
        cls,
        site_url: str,
        start_date: date,
        end_date: date,
        api_rows: list[dict],
    ) -> "GSCResponse":
        """Create response from GSC API data."""
        metrics = []
        total_clicks = 0
        total_impressions = 0

        for row in api_rows:
            keys = row.get("keys", [])
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)

            total_clicks += clicks
            total_impressions += impressions

            metrics.append(
                GSCMetric(
                    query=keys[0] if keys else "",
                    page=keys[1] if len(keys) > 1 else None,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=row.get("ctr", 0.0),
                    position=row.get("position", 0.0),
                )
            )

        avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0.0
        avg_position = (
            sum(m.position for m in metrics) / len(metrics) if metrics else 0.0
        )

        return cls(
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            total_queries=len(metrics),
            total_clicks=total_clicks,
            total_impressions=total_impressions,
            average_ctr=avg_ctr,
            average_position=avg_position,
        )
