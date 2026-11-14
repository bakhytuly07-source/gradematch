"""Bounded business instruments; no provider is created here."""
import os

from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation

RENDER_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5)
REASONS = frozenset({'invalid_request', 'too_large', 'invalid_image', 'processing_error'})


def views():
    return [View(instrument_name='gradematch_lut_render_seconds',
                 aggregation=ExplicitBucketHistogramAggregation(RENDER_BUCKETS))]


class BusinessMetrics:
    def __init__(self, meter):
        self.labels = {'environment': os.getenv('DEPLOYMENT_ENVIRONMENT', 'local'),
                       'version': os.getenv('APP_VERSION', 'dev')}
        self.counters = {name: meter.create_counter('gradematch_' + name) for name in (
            'styles_generated', 'generate_failures', 'looks_saved', 'users_registered')}
        # Name includes seconds; omit unit to avoid duplicate suffixes in Prometheus.
        self.render = meter.create_histogram('gradematch_lut_render_seconds')

    def add(self, name, reason=None):
        attrs = dict(self.labels)
        if reason is not None:
            if reason not in REASONS:
                raise ValueError('Unknown bounded failure reason')
            attrs['reason'] = reason
        self.counters[name].add(1, attrs)

    def rendered(self, seconds):
        self.render.record(seconds, self.labels)


def count(request, name, reason=None):
    metrics = request.app.state.business_metrics
    if metrics is not None:
        metrics.add(name, reason)
