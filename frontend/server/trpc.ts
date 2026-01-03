import { initTRPC, TRPCError } from "@trpc/server";
import superjson from "superjson";
import { ZodError } from "zod";
import { createClient } from "@/lib/supabase/server";
import type { User } from "@supabase/supabase-js";

/**
 * Supabase client type for tRPC procedures.
 *
 * Note: Using 'any' here because the generated Database types don't include
 * all tables that exist in the actual database (e.g., subscriptions, projects,
 * render_jobs, etc.). This is a workaround until the types are regenerated
 * from the live schema using `supabase gen types`.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type TypedSupabaseClient = any;

/**
 * tRPC context available in all procedures.
 *
 * @property supabase - Supabase client for database operations
 * @property user - Authenticated user or null for public routes
 * @property headers - Request headers for accessing cookies, auth tokens, etc.
 */
export interface TRPCContext {
  supabase: TypedSupabaseClient;
  user: User | null;
  headers: Headers;
}

export const createTRPCContext = async (opts: { headers: Headers }): Promise<TRPCContext> => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    supabase: supabase as any,
    user,
    headers: opts.headers,
  };
};

const t = initTRPC.context<TRPCContext>().create({
  transformer: superjson,
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

export const createCallerFactory = t.createCallerFactory;
export const createTRPCRouter = t.router;

// Public procedure - no auth required
export const publicProcedure = t.procedure;

// Protected procedure - requires authenticated user
export const protectedProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED" });
  }
  return next({
    ctx: {
      ...ctx,
      user: ctx.user,
    },
  });
});
