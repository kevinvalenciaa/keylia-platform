"use client";

import { useState } from "react";
import Link from "next/link";
import { trpc } from "@/lib/trpc/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { isValidImageUrl, sanitizeImageUrl } from "@/lib/utils";
import {
  Plus,
  Home,
  Bed,
  Bath,
  Square,
  Loader2,
  Sparkles,
  Pencil,
  Trash2,
} from "lucide-react";

// Status filter options - matches backend listingStatusEnum
const STATUS_FILTERS = [
  { value: "all", label: "All" },
  { value: "for_sale", label: "For Sale" },
  { value: "pending", label: "Pending" },
  { value: "sold", label: "Sold" },
] as const;

type StatusFilterValue = "all" | "for_sale" | "pending" | "sold" | "withdrawn" | "active";

export default function ListingsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilterValue>("all");

  // tRPC provides proper type inference - no manual casting needed
  const { data: listingsData, isLoading, refetch } = trpc.listing.list.useQuery({
    status: statusFilter === "all" ? undefined : statusFilter,
    limit: 50,
  });

  const deleteListing = trpc.listing.delete.useMutation({
    onSuccess: () => refetch(),
  });

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this listing?")) {
      await deleteListing.mutateAsync({ id });
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Listings</h1>
          <p className="text-muted-foreground mt-1">
            Manage your property listings
          </p>
        </div>
        <Button asChild>
          <Link href="/listings/new">
            <Plus className="w-4 h-4 mr-2" />
            Add Listing
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {STATUS_FILTERS.map((filter) => (
          <Button
            key={filter.value}
            variant={statusFilter === filter.value ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter(filter.value)}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      {/* Listings Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : !listingsData || listingsData.listings.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Home className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold mb-2">No listings yet</h3>
            <p className="text-muted-foreground mb-4">
              Add your first listing to start generating content
            </p>
            <Button asChild>
              <Link href="/listings/new">
                <Plus className="w-4 h-4 mr-2" />
                Add Listing
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {listingsData.listings.map((listing) => (
            <Card key={listing.id} className="overflow-hidden group">
              {/* Photo - XSS-safe image rendering */}
              <div className="aspect-video bg-muted relative">
                {listing.photos &&
                listing.photos.length > 0 &&
                isValidImageUrl(listing.photos[0]) ? (
                  <img
                    src={sanitizeImageUrl(listing.photos[0])}
                    alt={listing.address}
                    className="w-full h-full object-cover"
                    referrerPolicy="no-referrer"
                    loading="lazy"
                    onError={(e) => {
                      // Hide broken images gracefully
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Home className="w-12 h-12 text-muted-foreground" />
                  </div>
                )}
                <div className="absolute top-2 right-2">
                  <span
                    className={`px-2 py-1 text-xs rounded font-medium ${
                      listing.status === "active"
                        ? "bg-green-500 text-white"
                        : listing.status === "pending"
                        ? "bg-yellow-500 text-black"
                        : listing.status === "sold"
                        ? "bg-blue-500 text-white"
                        : "bg-gray-500 text-white"
                    }`}
                  >
                    {listing.status}
                  </span>
                </div>

                {/* Hover Actions */}
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <Button size="sm" variant="secondary" asChild>
                    <Link href={`/listings/${listing.id}`}>
                      <Sparkles className="w-4 h-4 mr-1" />
                      Generate
                    </Link>
                  </Button>
                  <Button size="sm" variant="secondary" asChild>
                    <Link href={`/listings/${listing.id}/edit`}>
                      <Pencil className="w-4 h-4" />
                    </Link>
                  </Button>
                </div>
              </div>

              <CardContent className="p-4">
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{listing.address}</h3>
                      <p className="text-sm text-muted-foreground">
                        {listing.city}, {listing.state} {listing.zip}
                      </p>
                    </div>
                    <button
                      className="p-1 hover:bg-muted rounded"
                      onClick={() => handleDelete(listing.id)}
                    >
                      <Trash2 className="w-4 h-4 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>

                  <p className="text-xl font-bold">
                    ${listing.price.toLocaleString()}
                  </p>

                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Bed className="w-4 h-4" /> {listing.bedrooms}
                    </span>
                    <span className="flex items-center gap-1">
                      <Bath className="w-4 h-4" /> {listing.bathrooms}
                    </span>
                    <span className="flex items-center gap-1">
                      <Square className="w-4 h-4" /> {listing.sqft.toLocaleString()}
                    </span>
                  </div>

                  {listing.features && listing.features.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-2">
                      {listing.features.slice(0, 3).map((feature) => (
                        <span
                          key={feature}
                          className="text-xs px-2 py-0.5 bg-muted rounded-full"
                        >
                          {feature}
                        </span>
                      ))}
                      {listing.features.length > 3 && (
                        <span className="text-xs text-muted-foreground">
                          +{listing.features.length - 3} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {listingsData && listingsData.total > 50 && (
        <p className="text-center text-muted-foreground text-sm">
          Showing 50 of {listingsData.total} listings
        </p>
      )}
    </div>
  );
}
