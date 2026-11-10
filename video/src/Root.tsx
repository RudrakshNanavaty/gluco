import { Composition } from "remotion"
import { TEASER_FRAMES, Teaser } from "./Teaser"
import { FPS, HEIGHT, WIDTH } from "./theme"
import { WALKTHROUGH_FRAMES, Walkthrough } from "./Walkthrough"

export function Root() {
  return (
    <>
      <Composition id="Teaser" component={Teaser} durationInFrames={TEASER_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
      <Composition id="Walkthrough" component={Walkthrough} durationInFrames={WALKTHROUGH_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
    </>
  )
}
