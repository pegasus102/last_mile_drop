// policy.cedar
// Last-Mile Whisper — Proximity-Based Privacy Guardrails
// Enforced via Cedar Policy Engine

// Policy 1: Landmark data is readable only when the driver is
// on duty and within 500 meters of the delivery pin.
permit (
    principal == User::"DeliveryDriver",
    action == Action::"ReadLandmark",
    resource == Package::"VoiceData"
)
when {
    context.driver_status == "ON_DUTY" &&
    context.distance_meters <= 500
};

// Policy 2: Digital Doorbell ping is permitted only when the driver
// is on duty and within 20 meters of the delivery pin.
permit (
    principal == User::"DeliveryDriver",
    action == Action::"PingDoorbell",
    resource == Package::"DeliverySession"
)
when {
    context.driver_status == "ON_DUTY" &&
    context.distance_meters <= 20
};
