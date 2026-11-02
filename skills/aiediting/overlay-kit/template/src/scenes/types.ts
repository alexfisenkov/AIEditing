import React from "react";

// A scene lives on [from, to) seconds of the video; the component reads the time itself through useT()
export type Scene = { from: number; to: number; C: React.FC };
