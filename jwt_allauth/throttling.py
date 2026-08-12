class ExtraThrottlesMixin:
    """
    Add the throttles a view needs on top of the project's defaults.

    DRF resolves throttling from ``throttle_classes``, which defaults to
    ``DEFAULT_THROTTLE_CLASSES``: a view that declares the attribute replaces that
    default instead of adding to it. The endpoints of this library are exactly the
    ones a project is most likely to have tightened, so declaring
    ``throttle_classes = [AnonRateThrottle]`` on them silently removed whatever the
    project had configured -- a ``ScopedRateThrottle`` capping registrations at
    ``5/min`` gave way to the ``60/min`` ``anon`` rate.

    The views declare their own throttles in ``extra_throttle_classes`` instead, and
    this mixin appends them to whatever ``throttle_classes`` resolves to. A class
    already present in the defaults is not added twice: two instances of the same
    throttle would consume the same bucket twice and halve the effective rate.

    DRF's semantics are untouched for projects that want full control: overriding
    ``throttle_classes`` on a subclass still replaces the defaults, and setting
    ``extra_throttle_classes = ()`` drops the additions of the library.
    """

    extra_throttle_classes = ()

    def get_throttles(self):
        """
        Build the throttles applied to the request.

        Returns:
            list: Instances of ``throttle_classes`` -- the project defaults unless the
            view overrides them -- followed by the ``extra_throttle_classes`` they do
            not already cover.
        """
        throttles = list(super().get_throttles())
        configured = {type(throttle) for throttle in throttles}
        throttles.extend(
            throttle_class()
            for throttle_class in self.extra_throttle_classes
            if throttle_class not in configured
        )
        return throttles
