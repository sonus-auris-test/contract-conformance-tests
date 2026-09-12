import "@typespec/json-schema";
using TypeSpec.JsonSchema;

namespace SonusAuris.Audio;

@id("AudioWindowDescriptorV1")
model AudioWindowDescriptorV1 {
  @minValue(1)
  @maxValue(1)
  version: integer;

  @minValue(8000)
  @maxValue(192000)
  sample_rate_hz: integer;

  @minValue(1)
  @maxValue(1000000)
  frame_count: integer;

  @minLength(1)
  @maxLength(128)
  label: string;

  speech_detected: boolean;
}
