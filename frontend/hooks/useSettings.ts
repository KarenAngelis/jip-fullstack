// web/hooks/useSettings.ts
import { useCallback, useEffect, useRef, useState } from "react";
import {
  apiGetMySettings,
  apiPutMySettings,
  apiPatchMySettings,
  apiUploadMySettingsMedia,
  type TSettingsOut,
  type TSettingsPutBody,
  type TSettingsPatchBody,
} from "../lib/settings";

type Status = "idle" | "loading" | "success" | "error";

export type UseSettingsOptions = {
  enabled?: boolean; // default true
};

export function useSettings(opts: UseSettingsOptions = {}) {
  const { enabled = true } = opts;

  const [data, setData] = useState<TSettingsOut | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<Error | null>(null);

  const [saving, setSaving] = useState(false);
  const [patching, setPatching] = useState(false);
  const [uploading, setUploading] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const refetch = useCallback(async () => {
    cancel();
    const ctl = new AbortController();
    abortRef.current = ctl;

    setStatus("loading");
    setError(null);
    try {
      const res = await apiGetMySettings();
      setData(res);
      setStatus("success");
      return res;
    } catch (err: unknown) {
      if (ctl.signal.aborted) return;
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      setStatus("error");
      throw e;
    }
  }, [cancel]);

  const save = useCallback(
    async (body: TSettingsPutBody) => {
      setSaving(true);
      setError(null);
      try {
        const res = await apiPutMySettings(body);
        setData(res);
        setSaving(false);
        return res;
      } catch (err: unknown) {
        const e = err instanceof Error ? err : new Error(String(err));
        setSaving(false);
        setError(e);
        throw e;
      }
    },
    []
  );

  const patch = useCallback(
    async (partial: TSettingsPatchBody) => {
      setPatching(true);
      setError(null);
      setData((prev: TSettingsOut | null) =>
        prev ? ({ ...prev, ...partial } as TSettingsOut) : prev
      );
      try {
        const res = await apiPatchMySettings(partial);
        setData(res);
        setPatching(false);
        return res;
      } catch (err: unknown) {
        setPatching(false);
        refetch().catch(() => {});
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        throw e;
      }
    },
    [refetch]
  );

  const uploadMedia = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      try {
        const { url } = await apiUploadMySettingsMedia(file);
        const refreshed = await refetch();
        setUploading(false);
        return { url, data: refreshed ?? null };
      } catch (err: unknown) {
        const e = err instanceof Error ? err : new Error(String(err));
        setUploading(false);
        setError(e);
        throw e;
      }
    },
    [refetch]
  );

  useEffect(() => {
    if (enabled) refetch();
    return () => cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return {
    data,
    status,
    error,
    refetch,
    save,
    patch,
    uploadMedia,
    cancel,
    isLoading: status === "loading",
    isError: status === "error",
    isSuccess: status === "success",
    saving,
    patching,
    uploading,
  };
}
