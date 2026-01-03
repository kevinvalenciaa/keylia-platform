"use client";

import { useState } from "react";
import Link from "next/link";
import { trpc } from "@/lib/trpc/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import {
  ImageIcon,
  Download,
  Loader2,
  Search,
  Copy,
  ExternalLink,
  Play,
  Video,
  Trash2,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Define content type for proper TypeScript inference
interface ContentPiece {
  id: string;
  user_id: string;
  listing_id: string;
  content_type: string;
  format: string;
  caption: string | null;
  hashtags: string[] | null;
  image_url: string | null;
  video_url: string | null;
  status: string;
  download_count: number;
  created_at: string;
  updated_at: string;
  listings?: {
    address: string;
    city: string;
    state: string;
    price: number;
  } | null;
}

const CONTENT_TYPE_FILTERS = [
  { value: "all", label: "All Types" },
  { value: "just_listed", label: "Just Listed" },
  { value: "just_sold", label: "Just Sold" },
  { value: "open_house", label: "Open House" },
  { value: "price_drop", label: "Price Drop" },
  { value: "coming_soon", label: "Coming Soon" },
];

export default function ContentPage() {
  const { toast } = useToast();
  const [typeFilter, setTypeFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [contentToDelete, setContentToDelete] = useState<ContentPiece | null>(null);

  const utils = trpc.useUtils();
  const { data: contentData, isLoading } = trpc.content.list.useQuery({
    content_type: typeFilter === "all" ? undefined : typeFilter as "just_listed" | "just_sold" | "open_house" | "price_drop" | "coming_soon",
    limit: 50,
  });
  const { data: stats } = trpc.content.getStats.useQuery();
  const trackDownload = trpc.content.trackDownload.useMutation();
  const deleteContent = trpc.content.delete.useMutation({
    onSuccess: () => {
      utils.content.list.invalidate();
      utils.content.getStats.invalidate();
      toast({
        title: "Deleted",
        description: "Content has been permanently deleted.",
      });
      setContentToDelete(null);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to delete content.",
        variant: "destructive",
      });
    },
  });

  const handleDownload = async (contentId: string, mediaUrl?: string | null, isVideo: boolean = false) => {
    await trackDownload.mutateAsync({ id: contentId });

    if (mediaUrl) {
      // Trigger actual download
      const link = document.createElement("a");
      link.href = mediaUrl;
      link.download = `content-${contentId}.${isVideo ? "mp4" : "png"}`;
      link.click();
    }

    toast({
      title: "Downloaded!",
      description: "Content downloaded successfully.",
    });
  };

  const copyCaption = (caption: string) => {
    navigator.clipboard.writeText(caption);
    toast({
      title: "Copied!",
      description: "Caption copied to clipboard.",
    });
  };

  const copyHashtags = (hashtags: string[]) => {
    navigator.clipboard.writeText(hashtags.map((h) => `#${h}`).join(" "));
    toast({
      title: "Copied!",
      description: "Hashtags copied to clipboard.",
    });
  };

  const handleDelete = () => {
    if (contentToDelete) {
      deleteContent.mutate({ id: contentToDelete.id });
    }
  };

  const content = (contentData?.content ?? []) as ContentPiece[];
  const filteredContent = content.filter((c) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      c.caption?.toLowerCase().includes(query) ||
      c.content_type.toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Content Library</h1>
          <p className="text-muted-foreground mt-1">
            All your generated social media content
          </p>
        </div>
        <Button asChild>
          <Link href="/listings">Generate New</Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
            <p className="text-xs text-muted-foreground">Total Content</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{stats?.drafts || 0}</div>
            <p className="text-xs text-muted-foreground">Drafts</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{stats?.downloaded || 0}</div>
            <p className="text-xs text-muted-foreground">Downloaded</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{stats?.totalDownloads || 0}</div>
            <p className="text-xs text-muted-foreground">Total Downloads</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search content..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {CONTENT_TYPE_FILTERS.map((filter) => (
                <Button
                  key={filter.value}
                  variant={typeFilter === filter.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTypeFilter(filter.value)}
                >
                  {filter.label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Content Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : !filteredContent || filteredContent.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold mb-2">No content found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || typeFilter !== "all"
                ? "Try adjusting your filters"
                : "Generate your first content piece from a listing"}
            </p>
            <Button asChild>
              <Link href="/listings/new">Add a Listing</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredContent.map((contentItem) => (
            <Card key={contentItem.id} className="overflow-hidden group/card">
              {/* Media Preview */}
              <div className="aspect-[9/16] bg-muted relative group">
                {contentItem.video_url ? (
                  <video
                    src={contentItem.video_url}
                    className="w-full h-full object-cover"
                    muted
                    playsInline
                    preload="metadata"
                    onMouseEnter={(e) => e.currentTarget.play()}
                    onMouseLeave={(e) => {
                      e.currentTarget.pause();
                      e.currentTarget.currentTime = 0;
                    }}
                  />
                ) : contentItem.image_url ? (
                  <img
                    src={contentItem.image_url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-2">
                    <Video className="w-12 h-12 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Processing...</span>
                  </div>
                )}
                {/* Play icon overlay for videos */}
                {contentItem.video_url && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-100 group-hover:opacity-0 transition-opacity">
                    <div className="w-12 h-12 bg-black/50 rounded-full flex items-center justify-center">
                      <Play className="w-6 h-6 text-white fill-white ml-1" />
                    </div>
                  </div>
                )}
                <div className="absolute top-2 left-2 flex gap-1">
                  <span className="px-2 py-1 bg-black/60 text-white text-xs rounded capitalize">
                    {contentItem.content_type.replace("_", " ")}
                  </span>
                  {contentItem.video_url && (
                    <span className="px-2 py-1 bg-primary/80 text-white text-xs rounded flex items-center gap-1">
                      <Video className="w-3 h-3" />
                      Video
                    </span>
                  )}
                </div>
                <div className="absolute top-2 right-2">
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      contentItem.status === "completed"
                        ? "bg-green-500 text-white"
                        : contentItem.status === "downloaded"
                        ? "bg-green-500 text-white"
                        : contentItem.status === "published"
                        ? "bg-blue-500 text-white"
                        : contentItem.status === "rendering"
                        ? "bg-orange-500 text-white"
                        : "bg-yellow-500 text-black"
                    }`}
                  >
                    {contentItem.status}
                  </span>
                </div>
              </div>

              <CardContent className="p-4 space-y-4">
                {/* Listing Info */}
                {contentItem.listings && (
                  <div className="text-sm">
                    <Link
                      href={`/listings/${contentItem.listing_id}`}
                      className="font-medium hover:underline flex items-center gap-1"
                    >
                      {contentItem.listings.address}
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                    <p className="text-muted-foreground">
                      {contentItem.listings.city}, {contentItem.listings.state} •{" "}
                      ${contentItem.listings.price.toLocaleString()}
                    </p>
                  </div>
                )}

                {/* Caption Preview */}
                {contentItem.caption && (
                  <div className="space-y-2">
                    <p className="text-sm line-clamp-3">{contentItem.caption}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyCaption(contentItem.caption!)}
                    >
                      <Copy className="w-3 h-3 mr-1" />
                      Copy Caption
                    </Button>
                  </div>
                )}

                {/* Hashtags */}
                {contentItem.hashtags && contentItem.hashtags.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-1">
                      {contentItem.hashtags.slice(0, 5).map((tag) => (
                        <span key={tag} className="text-xs text-primary">
                          #{tag}
                        </span>
                      ))}
                      {contentItem.hashtags.length > 5 && (
                        <span className="text-xs text-muted-foreground">
                          +{contentItem.hashtags.length - 5} more
                        </span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyHashtags(contentItem.hashtags!)}
                    >
                      <Copy className="w-3 h-3 mr-1" />
                      Copy Hashtags
                    </Button>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    className="flex-1"
                    onClick={() => handleDownload(
                      contentItem.id,
                      contentItem.video_url || contentItem.image_url,
                      !!contentItem.video_url
                    )}
                    disabled={!contentItem.video_url && !contentItem.image_url}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    {contentItem.video_url ? "Download Video" : "Download"}
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href={`/listings/${contentItem.listing_id}`}>Edit</Link>
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => setContentToDelete(contentItem)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                {/* Download Count */}
                {contentItem.download_count > 0 && (
                  <p className="text-xs text-center text-muted-foreground">
                    Downloaded {contentItem.download_count} time
                    {contentItem.download_count !== 1 ? "s" : ""}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!contentToDelete} onOpenChange={(open) => !open && setContentToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Content</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this content? This action cannot be undone and will permanently remove the content from your library.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteContent.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteContent.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteContent.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
