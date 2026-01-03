import { createTRPCRouter } from "../trpc";
import { profileRouter } from "./profile";
import { listingRouter } from "./listing";
import { contentRouter } from "./content";
import { aiRouter } from "./ai";
import { billingRouter } from "./billing";
import { tourVideoRouter } from "./tourVideo";

export const appRouter = createTRPCRouter({
  profile: profileRouter,
  listing: listingRouter,
  content: contentRouter,
  ai: aiRouter,
  billing: billingRouter,
  tourVideo: tourVideoRouter,
});

export type AppRouter = typeof appRouter;
