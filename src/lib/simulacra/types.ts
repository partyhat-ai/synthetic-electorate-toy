// Small view types shared by the page and its components.

/** Where a vote lands on screen: the winner (A), the runner-up (B), or everyone else (O). */
export type Bucket = 'A' | 'B' | 'O';

/** A fill per bucket, authored for the current mode (palette.ts paint). */
export type Colors = Readonly<Record<Bucket, string>>;

/** A surname per bucket; B is absent when the winner ran unopposed. */
export interface Names {
  readonly A: string;
  readonly B?: string | undefined;
  readonly O: string;
}
