"use client";

import Link from "next/link";
import { trpc } from "@/lib/trpc/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Plus,
  ArrowRight,
  Home,
  ImageIcon,
  Download,
  Sparkles,
  Loader2,
} from "lucide-react";

// Type definitions for proper TypeScript inference
interface Profile {
  full_name: string | null;
  business_name: string | null;
}

interface ContentPiece {
  id: string;
  content_type: string;
  caption: string | null;
  image_url: string | null;
  status: string;
  download_count: number;
}

interface Listing {
  id: string;
  address: string;
  price: number;
  status: string;
}

export default function DashboardPage() {
  const { data: profileData } = trpc.profile.get.useQuery();
  const profile = profileData as Profile | null | undefined;
  const { data: usage } = trpc.billing.getUsage.useQuery();
  const { data: listingsRaw } = trpc.listing.list.useQuery({ limit: 5 });
  const { data: contentRaw } = trpc.content.list.useQuery({ limit: 6 });
  const { data: stats } = trpc.content.getStats.useQuery();

  // Cast data for proper TypeScript inference
  const listingsData = listingsRaw as { listings: Listing[]; total: number } | undefined;
  const contentData = contentRaw as { content: ContentPiece[]; total: number } | undefined;

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold">
          Welcome back{profile?.full_name ? `, ${profile.full_name.split(" ")[0]}` : ""}!
        </h1>
        <p className="text-muted-foreground mt-1">
          Create stunning content for your listings in minutes.
        </p>
      </div>

      {/* Trial Banner */}
      {usage?.isTrial && (
        <Card className="border-yellow-200 bg-yellow-50 dark:bg-yellow-950/20">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-yellow-600" />
                <div>
                  <p className="font-medium text-yellow-900 dark:text-yellow-100">
                    Free Trial Active
                  </p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300">
                    {5 - (usage.used || 0)} content pieces remaining
                  </p>
                </div>
              </div>
              <Button asChild variant="outline" className="border-yellow-300">
                <Link href="/pricing">Upgrade</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Create</CardTitle>
          <CardDescription>
            Add a listing and generate social media content
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <Link href="/listings/new" className="group">
              <div className="flex items-center gap-4 p-4 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer">
                <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Home className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-semibold">Add New Listing</h3>
                  <p className="text-sm text-muted-foreground">
                    Upload photos & property details
                  </p>
                </div>
              </div>
            </Link>

            {listingsData && listingsData.listings.length > 0 && (
              <Link
                href={`/listings/${listingsData.listings[0].id}`}
                className="group"
              >
                <div className="flex items-center gap-4 p-4 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer">
                  <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Sparkles className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Generate Content</h3>
                    <p className="text-sm text-muted-foreground">
                      Create posts for existing listings
                    </p>
                  </div>
                </div>
              </Link>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stats and Listings */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Content */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Content</CardTitle>
              <CardDescription>Your latest generated posts</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/content">
                View All
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {!contentData ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : contentData.content.length === 0 ? (
              <div className="text-center py-8">
                <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No content generated yet</p>
                <Button asChild variant="link" className="mt-2">
                  <Link href="/listings/new">Add your first listing</Link>
                </Button>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {contentData.content.map((content) => (
                  <div
                    key={content.id}
                    className="group relative rounded-lg border overflow-hidden hover:shadow-md transition-shadow"
                  >
                    <div className="aspect-square bg-muted flex items-center justify-center relative">
                      {content.image_url ? (
                        <img
                          src={content.image_url}
                          alt=""
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <ImageIcon className="h-8 w-8 text-muted-foreground" />
                      )}
                      <span className="absolute top-2 right-2 text-xs px-2 py-0.5 rounded bg-black/60 text-white capitalize">
                        {content.content_type.replace("_", " ")}
                      </span>
                    </div>
                    <div className="p-3">
                      <p className="text-sm line-clamp-2 text-muted-foreground">
                        {content.caption || "No caption"}
                      </p>
                      <div className="flex items-center justify-between mt-2">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            content.status === "downloaded"
                              ? "bg-green-100 text-green-700"
                              : content.status === "published"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {content.status}
                        </span>
                        {content.download_count > 0 && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Download className="w-3 h-3" />
                            {content.download_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Content Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <p className="text-2xl font-bold">{stats?.total || 0}</p>
                  <p className="text-xs text-muted-foreground">Total Created</p>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <p className="text-2xl font-bold">{stats?.totalDownloads || 0}</p>
                  <p className="text-xs text-muted-foreground">Downloads</p>
                </div>
              </div>
              {usage && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Usage this month</span>
                    <span className="font-medium">
                      {usage.used} / {usage.limit === -1 ? "Unlimited" : usage.limit}
                    </span>
                  </div>
                  {usage.limit !== -1 && usage.limit != null && usage.limit > 0 && (
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all"
                        style={{
                          width: `${Math.min((usage.used / usage.limit) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active Listings */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">Your Listings</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/listings">View All</Link>
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {!listingsData ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : listingsData.listings.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-sm text-muted-foreground mb-2">
                    No listings yet
                  </p>
                  <Button asChild size="sm">
                    <Link href="/listings/new">
                      <Plus className="w-4 h-4 mr-1" />
                      Add Listing
                    </Link>
                  </Button>
                </div>
              ) : (
                <>
                  {listingsData.listings.map((listing) => (
                    <Link
                      key={listing.id}
                      href={`/listings/${listing.id}`}
                      className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                    >
                      <Home className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">
                          {listing.address}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          ${listing.price.toLocaleString()} •{" "}
                          <span className="capitalize">{listing.status}</span>
                        </p>
                      </div>
                      <Button size="sm" variant="ghost" className="h-8">
                        <Sparkles className="h-4 w-4" />
                      </Button>
                    </Link>
                  ))}
                  {listingsData.total > 5 && (
                    <Button asChild variant="ghost" className="w-full" size="sm">
                      <Link href="/listings">
                        View all {listingsData.total} listings
                      </Link>
                    </Button>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
