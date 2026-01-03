import "server-only";

import { createTRPCContext } from "@/server/trpc";
import { appRouter } from "@/server/routers/_app";
import { createCallerFactory } from "@/server/trpc";

const createCaller = createCallerFactory(appRouter);

export const api = async () => {
  const context = await createTRPCContext({ headers: new Headers() });
  return createCaller(context);
};
